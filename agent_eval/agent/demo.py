"""Run the deterministic refund example with ``python -m agent_eval.agent.demo``."""

from agent_eval.agent import Agent, FakeLLM, create_default_tools


def main() -> None:
    agent = Agent(llm=FakeLLM(), tools=create_default_tools())
    result = agent.run("Refund order 1234")

    print("Final response:")
    print(result.final_response)
    print("\nTool calls:")
    for index, tool_call in enumerate(result.tool_calls, start=1):
        print(f"{index}. {tool_call.name}")


if __name__ == "__main__":
    main()
