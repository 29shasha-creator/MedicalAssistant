import logging
import datetime

def setup_logger():
    log_filename = f"pipeline_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    logger = logging.getLogger("medical_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()          # prevent duplicate handlers on re-run
    logger.propagate = False         # don't bubble up to root logger

    # File only
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    # Suppress noisy third-party loggers
    for noisy in ["httpx", "openai", "httpcore", "urllib3"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.info(f"Logging to: {log_filename}")
    return logger

logger = setup_logger()

from langgraph.graph import StateGraph,START,END
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from langgraph.graph.message import BaseMessage,add_messages
from langchain_core.runnables.graph import MermaidDrawMethod
from typing import TypedDict,Literal,Annotated,Any,NotRequired
# from IPython.display import display,Image,Markdown
from dotenv import load_dotenv
from Bio import Entrez
import os
import json
import requests
import re

env_path = r"C:\Photo\Photo\MyLearning\Agentic AI\Python\.env"
load_dotenv(env_path)
#os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["NCBI_API_KEY"] = os.getenv("NCBI_API_KEY")
os.environ["PUBMED_EMAIL"] = os.getenv("PUBMED_EMAIL")

Entrez.email = os.getenv("PUBMED_EMAIL")
Entrez.api_key = os.getenv("NCBI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini",temperature=0)
#llm = ChatGroq(model="llama-3.3-70b-versatile", temperature = 0)
class State(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]
    search_queries:list[str]
    xmlcontent:Any
    documents:list[Document]
    filtered_documents:list[Document]
    context:str
    reasoning:str
    validation:str
    needs_more_retrieval:bool
    final_response:str
    relevant_documents:list[Document]
    retry_count: NotRequired[int]

def medical_planner(state:State):

    question = state["messages"][-1].content

    planner_prompt = f"""You are a medical research planning agent.
    Convert this clinical question into 4 specific PubMed search queries.

    User question: {question}

    Instructions:
    - Extract the PRIMARY disease from the question — use its full clinical name
      Example: "pancreatic cancer" → use "pancreatic ductal adenocarcinoma" OR "pancreatic cancer gemcitabine"
      Example: "brain tumour" → use "glioblastoma temozolomide" OR "glioma bevacizumab"
    - Extract the COMORBIDITY — include it in at least 2 queries
    - Every query must have 3-5 words minimum — never single topic queries
    - Use specific drug names, gene names, or treatment modalities
    - Do NOT generate vague queries

    Return ONLY a valid JSON array of 4 strings.
    No explanation, no markdown.
    """

    response = llm.invoke(planner_prompt)
    
# This will convert this into python list
    raw_output = response.content.strip()
    
    try:
        
        queries = json.loads(raw_output)

    except json.JSONDecodeError:
        # Remove markdown if present
        cleaned = re.sub(r"```json|```", "", raw_output).strip()

        queries = json.loads(cleaned)
    # Safety check
    if not isinstance(queries, list) or len(queries) == 0:
        raise ValueError(f"Planner returned invalid queries: {raw_output}")

    logger.info("[Planner] Generated queries:")
    for i, q in enumerate(queries, 1):
        logger.info(f"  {i}. {q}")
        
    return {"search_queries":queries}

def bio_efetch(state:State):
    """Fetch PubMed papers using multiple agent-generated queries."""
    all_articles = []
    retry_count = state.get("retry_count",0)
    retmax = 15 + (retry_count*10)
    
    for query in state['search_queries']:

         # Try strictest filter first
        filters = [
            f"{query} AND humans[mesh] AND english[lang] AND (clinical trial[pt] OR review[pt])",
            f"{query} AND humans[mesh] AND english[lang]",   # drop pub type
            f"{query} AND english[lang]",                    # drop humans mesh
            f"{query}",                                      # bare query
        ]
        
        pmid = []
        used_filter = ""

        for filter_query in filters:
            handle = Entrez.esearch(
                db="pubmed",
                term = filter_query,
                retmax = retmax,
                sort = "pub date"
            )
            results = Entrez.read(handle)
            pmid = results["IdList"]
            handle.close()
            used_filter = filter_query

            if pmid:
                logger.info(f"[Efetch] Query succeeded with filter level {filters.index(filter_query)+1}")
                logger.info(f"[Efetch] PMIDs found: {len(pmid)}")
                break
            else:
                logger.info(f"[Efetch] No results, relaxing filter...")
                
        #Skip if no papers found
        if not pmid:
            logger.info(f"[Efetch] No results for query: {query[:60]}")
            continue
    
        fetch_handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmid),
            retmode = "xml"
        )
        papers = Entrez.read(fetch_handle)
        fetch_handle.close()

        #Merge all retrieved articles
        all_articles.extend(
            papers.get("PubmedArticle",[])
        )
        
    logger.info(f"[Efetch] Total articles fetched: {len(all_articles)}")
    return {"xmlcontent":{
        "PubmedArticle":all_articles
    }
           }

def create_document(state:State):
    """Create LangChain Documents from PubMed articles."""
    #LangChain Documents
    documents = []
    papers = state['xmlcontent']
    
    for article in papers["PubmedArticle"]:
        
        article_data = article["MedlineCitation"]["Article"]
        
        abstract = " ".join(
            article_data.get("Abstract",{})
                .get("AbstractText",[])
        )
        
        if not abstract.strip():
            continue
            
        author_list = article_data.get("AuthorList",[])
        authors = []
        for author in author_list:
            last = author.get("LastName","")
            fore = author.get("ForeName","")
            initials = author.get("Initials","")
            
            author_name = f"{last} {fore} {initials}".strip()
            if author_name:
                authors.append(author_name)

        authors_str = ";".join(authors)
            

        doc = Document(
            page_content=abstract,
            metadata={
                "pmid": str(article["MedlineCitation"]["PMID"]),
                "journal" : article_data.get("Journal",{}).get("Title",""),
                "title": article_data.get("ArticleTitle",""),
                "authors": authors_str,
                "year": article_data.get("Journal",{}).get("JournalIssue",{}).get("PubDate",{}).get("Year","")
            }
        )
        documents.append(doc)
    return {"documents":documents}

def filter_documents(state:State):
    """Fetch Latest treatments docs"""
    filtered = []
    unique_pmids = set()
    
    for doc in state["documents"]:
        pmid = doc.metadata.get("pmid")
        if pmid in unique_pmids:
            continue
            
        year = doc.metadata.get("year","")

        try:
            year_int = int(year)

        except:
            year_int = 0

        # keep recent papers
        if year_int >=1980:
            filtered.append(doc)
            unique_pmids.add(pmid)
            
    return{"filtered_documents":filtered}

def relevance_filter(state: State):
    """Keep Only Highly relevant Papers"""
    question = state["messages"][-1].content
    relevant_docs=[]
    
    logger.info(f"TOTAL FILTERED DOCS: , {len(state["filtered_documents"])}")
    
    for doc in state["filtered_documents"]:
        relevance_prompt=f"""Is this medical paper relevant to answering the user's question?
        User Question: {question}

        Papers:
        Title:{doc.metadata.get("title")}
        Abstract:{doc.page_content[:600]}

        A paper is RELEVANT if it covers ANY of:
        - The primary disease mentioned in the question
        - Treatments or drugs for that disease
        - Drug interactions or contraindications
        - Comorbidity management related to the question
        - Clinical outcomes or risks

        A paper is NOT RELEVANT only if it is about a completely different disease
        or has no connection to the question at all.

        Return ONLY: YES or NO
        """
        response = llm.invoke(relevance_prompt)
        answer = response.content.strip().upper()

        # Debug — print every decision
        logger.info(f"  {'✓' if 'YES' in answer else '✗'} [{answer}] {doc.metadata.get('title','')[:65]}")

        if "YES" in answer:
            relevant_docs.append(doc)
            
    logger.info(f"[Relevance] Kept {len(relevant_docs)} / {len(state['filtered_documents'])} documents")
    return {"relevant_documents":relevant_docs}
    

def build_context(state:State):

    docs = state["relevant_documents"]

    if not docs:
        return {"context": ""}

    MAX_CHARS_PER_DOC = 1500 # ~375 token - enough for full abstract
    MAX_DOCS = 10 # Top 10 Papers
    MAX_TOTAL_CHARS = 8000 # ~2000 tokens - leavesroom for prompts
    
    context_parts = []
    total_chars = 0

    for doc in docs[:MAX_DOCS]:
        abstract = doc.page_content
#Only trim when abstarct is too long

        if len(abstract)>MAX_CHARS_PER_DOC:
            abstract = abstract[:MAX_CHARS_PER_DOC] + "...."

        part = f"""
            PMID : {doc.metadata.get("pmid")}
            Title : {doc.metadata.get("title")}
            Year : {doc.metadata.get("year")}
            Abstract : {abstract}
            """
    #stop adding docs if we hit the ceiling 
        if total_chars + len(part) > MAX_TOTAL_CHARS:
            logger.info(f"[Context] reached ---- using {len(context_parts)} docs")
            break
        
        context_parts.append(part)
        total_chars = total_chars + len(part)
        
    context = "\n\n".join(context_parts)
    logger.info(f"[Context] Built: {len(context_parts)} docs | {total_chars} chars | ~{total_chars//4} tokens")
    return{"context":context}

def medical_reasoner(state:State):
    question = state["messages"][-1].content
    context = state["context"]

    if not context.strip():
        return {
            "reasoning": f"""Insufficient direct evidence found for: '{question}'

            Possible reasons:
            1. This combination is rare and understudied in medical literature
            2. Search queries may need refinement
            3. PubMed may not have indexed relevant papers yet. """ }

    SAFETY_LIMIT = 8000
    if len(context)>SAFETY_LIMIT:
        context = context[:SAFETY_LIMIT]
        logger.info(f"[Reasoner] Safety Trim Applied")

    response = llm.invoke(f"""You are an clinical reasoning assistant.
    Question:{question}
    
    Medical Evidence:{context}

    Rules:
    - Use ONLY provide evidence
    - Do NOT hallucinate
    - Every treatment claim MUST cite PMID
    - If evidence is insufficient, explicitly say so Tasks:
    1. Compare treatment options
    2. Mention benefits and risks
    3. Identify contraindications
    4. Mention comorbidity considerations
""")
    logger.info(f"[Reasoner] Reasoning generated : {len(response.content)} chars")
    return {"reasoning":response.content}
    

def validator(state: State):

    reasoning = state["reasoning"]
    context = state["context"]
    reasoning_trimmed = reasoning[:3000]
    context_trimmed = context[:3000]
    
    validator_prompt=f"""validate whether the answer is fully supported by retrieved medical evidence.

    Check:
    1. Disease consistency
    2. Treatment consistency
    3. PMID relevance
    4. Unsupported claims
    5. Hallucinated conditions
    6. Unrelated cancer types
    7. Missing citations

    Answer:{reasoning_trimmed}
    
    Evidenc:{context_trimmed}

    Returns ONLY : PASS or FAIL: <short reason>
    """

    response = llm.invoke(validator_prompt)
    validation = response.content.strip()
    needs_more = validation.startswith("FAIL")

    retry_count = state.get("retry_count", 0)

    if needs_more:
        retry_count += 1
        
    logger.info(f"[Validator] {validation}")
    logger.info(f"[Validator] Needs more retrieval: {needs_more}")
    
    return{
        "validation":validation,
        "needs_more_retrieval": needs_more,
        "retry_count": retry_count
    }

def response_generator(state: State):
    reasoning = state["reasoning"]

    final_prompt = f"""Creata a structured Evidence based clinical summary.
    Include:
    - Treatment Options
    - Risks
    - Contraindications
    - Clinical Considerations
    - PMID Citations

    Content:{reasoning}"""

    if "Insufficient medical evidence" in reasoning:
        return {
            "final_response":
            "Insufficient directly relevant PubMed evidence was retrieved for this query."
        }
        
    response = llm.invoke(final_prompt)
    
    return {"final_response":response.content}
    

def validation_router(state:State):
    retry_count = state.get("retry_count", 0)
    # Prevent infinite retrieval loop
    if state["retry_count"] >= 2:
        return "generate"
        
    if state["needs_more_retrieval"]:
        return "retrieve_again"

    return "generate"

# Build Graph

builder = StateGraph(State)

# Add NODES

builder.add_node("Medical Planner-Natural Language to Clinical Subqueries",medical_planner)
builder.add_node("API CALL-Fetch PubMed Research Papers",bio_efetch)
builder.add_node("XML PARSING-Build Structured LangChain Documents",create_document)
builder.add_node("Keeps Filtered Documents",filter_documents)
builder.add_node("Keeps Highly Releavnt Documents",relevance_filter)
builder.add_node("Build Contextual Documents",build_context)
builder.add_node("Build Clinical Answer",medical_reasoner)
builder.add_node("Answer is Grounded",validator)
builder.add_node("Generate Final response",response_generator)

# Add EDGES
builder.add_edge(START,"Medical Planner-Natural Language to Clinical Subqueries")
builder.add_edge("Medical Planner-Natural Language to Clinical Subqueries","API CALL-Fetch PubMed Research Papers")
builder.add_edge("API CALL-Fetch PubMed Research Papers","XML PARSING-Build Structured LangChain Documents")
builder.add_edge("XML PARSING-Build Structured LangChain Documents","Keeps Filtered Documents")
builder.add_edge("Keeps Filtered Documents","Keeps Highly Releavnt Documents")
builder.add_edge("Keeps Highly Releavnt Documents","Build Contextual Documents")
builder.add_edge("Build Contextual Documents","Build Clinical Answer")
builder.add_edge("Build Clinical Answer","Answer is Grounded")
builder.add_conditional_edges(
    "Answer is Grounded",validation_router,{"retrieve_again":"API CALL-Fetch PubMed Research Papers","generate":"Generate Final response"}
)
builder.add_edge("Generate Final response",END)

graphflow = builder.compile()