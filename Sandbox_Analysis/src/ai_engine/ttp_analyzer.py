from src.ai_engine.prompt_builder import PromptBuilder


class TTPAnalyzer:

    def __init__(self, llm_client):
        self.llm = llm_client

    def analyze(self, behavior_chain):

        prompt = PromptBuilder.build_ttp_prompt(behavior_chain)

        result = self.llm.generate(prompt)

        return result
