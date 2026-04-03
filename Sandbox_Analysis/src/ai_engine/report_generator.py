from src.ai_engine.prompt_builder import PromptBuilder


class AIReportGenerator:

    def __init__(self, llm_client):
        self.llm = llm_client

    def generate(self, behavior_chain, ttp_result):

        prompt = PromptBuilder.build_report_prompt(
            behavior_chain,
            ttp_result
        )

        report = self.llm.generate(prompt)

        return report
