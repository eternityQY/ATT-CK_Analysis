class PromptBuilder:

    @staticmethod
    def build_ttp_prompt(behavior_chain):

        prompt = f"""
You are a senior malware analyst.

The following text describes a malware behavior chain extracted from sandbox execution logs.

Your task is to identify attacker tactics and techniques using the MITRE ATT&CK framework.

Behavior Chain:
{behavior_chain}

Analysis Procedure:

Step 1. Identify suspicious behaviors.

Step 2. Determine attacker objectives.

Step 3. Map behaviors to MITRE ATT&CK tactics.

Step 4. Identify corresponding techniques.

Step 5. Explain reasoning.

Output Format:

TTPs:

- Tactic:
- Technique ID:
- Technique Name:
- Description:
- Evidence:

Limit results to the most relevant techniques.
"""

        return prompt

    @staticmethod
    def build_report_prompt(behavior_chain, ttp_result):

        prompt = f"""
You are a professional malware threat intelligence analyst.

Behavior Chain:
{behavior_chain}

Identified MITRE ATT&CK Techniques:
{ttp_result}

Generate a professional malware analysis report.

Report Structure:

1 Executive Summary

2 Behavior Analysis

3 Attack Chain Reconstruction

4 MITRE ATT&CK Mapping

5 Threat Assessment

The report must be clear, structured and technical.
"""

        return prompt
