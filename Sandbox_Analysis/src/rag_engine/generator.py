from typing import List, Dict
from src.utils.llm_client import LLMClient

class ReportGenerator:
    """
    Report Generator - The final step of the RAG pipeline
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_report(self, query: str, behavior_description: str, retrieved_docs: List[Dict]) -> str:
        """
        Generate Malware Analysis Report in English
        
        Args:
            query: User's original query or analysis intent
            behavior_description: Rewritten behavior chain description
            retrieved_docs: List of retrieved knowledge documents
        """
        # 1. Build the prompt (strictly in English)
        prompt = self._build_generation_prompt(query, behavior_description, retrieved_docs)
        
        # 2. Call LLM (Use lower temperature for factual accuracy)
        print("   [Generator] Asking LLM to generate final report...")
        report = self.llm_client.generate(prompt, temperature=0.4, max_tokens=3000)
        
        return report

    def _build_generation_prompt(self, query: str, behavior_desc: str, docs: List[Dict]) -> str:
        """Construct structured English Prompt"""
        
        # Format retrieved documents
        formatted_docs = ""
        for i, doc in enumerate(docs):
            source = doc.get("source", "Unknown")
            # Replace newlines to keep prompt compact
            content = doc.get("content", "").replace("\n", " ")
            formatted_docs += f"[{i+1}] Source: {source}\nContent: {content}\n\n"

        if not formatted_docs:
            formatted_docs = "No relevant technical documents found."

        # Prompt Template (English)
        prompt = f"""
You are a senior Malware Analysis Expert. Based on the provided information, generate a comprehensive malware analysis report.

### 1. Analysis Context
- **Objective/Query**: {query}

### 2. Observed Behavior (Reconstructed from Sandbox Logs)
{behavior_desc}

### 3. Reference Knowledge (ATT&CK / Threat Intel / API Docs)
{formatted_docs}

---

### Instructions
Generate a professional analysis report based on the observed behavior and reference knowledge. 
**You MUST output the report strictly in English.**

The report must include the following sections:

#### 1. Executive Summary
Briefly summarize the malware's main functionality, purpose, and execution flow.

#### 2. Technical Deep Dive
Analyze the technical details such as API calls, file operations, network communications, or process injection. Use the "Reference Knowledge" to explain the mechanism of these techniques.

#### 3. MITRE ATT&CK Mapping
List the Tactics and Techniques involved. Format as: ID (Name). Example: T1055 (Process Injection).

#### 4. Threat Level Assessment
Score: Low / Medium / High / Critical. Provide a justification for your score.

#### 5. Mitigation & Recommendations
Provide detection methods, defensive measures, or incident response recommendations.

Response Format: Markdown
"""
        return prompt