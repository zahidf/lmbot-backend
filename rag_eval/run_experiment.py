"""
Step 2: Run a RAG experiment against a Langfuse Dataset.

Each run is grouped under a named experiment.

Usage:
    python run_experiment.py --dataset sample --name baseline-v1
    python run_experiment.py --dataset full --name baseline-v1
    python run_experiment.py --dataset sample --name chunk-256 --description "Smaller chunks"

Requires: langfuse >= 4.0.0
"""

import argparse
import os

import requests
from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client, Evaluation
from openai import AsyncOpenAI
from ragas.embeddings import OpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerCorrectness, ContextRecall, Faithfulness


RAG_API_URL = os.getenv("RAG_API_URL")
RAG_API_TOKEN = os.getenv("RAG_API_TOKEN")
LANGFUSE_DATASET_NAMES = {
    "sample": "rag-eval-sample",
    "full": "rag-eval-full",
}


# ── Init ────────────────────────────────────────────────────
def init_langfuse():
    langfuse = get_client()
    return langfuse

def init_scorers():
    client = AsyncOpenAI()
    evaluator_llm = llm_factory("gpt-4.1-mini", client=client, max_tokens=8192)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", client=client)
    return {
        "answer_correctness": AnswerCorrectness(llm=evaluator_llm, embeddings=embeddings),
        "context_recall": ContextRecall(llm=evaluator_llm),
        "faithfulness": Faithfulness(llm=evaluator_llm),
    }


# ── Task function ───────────────────────────────────────────
# Called by run_experiment() for each dataset item.
# Must accept (*, item, **kwargs) and return the output.
def rag_task(*, item, **kwargs):
    """Call the RAG API for a single dataset item."""
    question = item.input["question"]

    headers = {"Content-Type": "application/json"}
    if RAG_API_TOKEN:
        headers["Authorization"] = f"Bearer {RAG_API_TOKEN}"

    resp = requests.post(RAG_API_URL, json={"query": question}, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    return {
        "response": data["response"],
        "contexts": [s["content"] for s in data.get("sources", [])],
    }


# ── Evaluator functions ─────────────────────────────────────
# Each evaluator is called per item with (*, input, output, expected_output, **kwargs)
# and must return an Evaluation object.

# Scorers are initialised in main() and injected via closure.
# Evaluators are async because Langfuse run_experiment() runs in an
# async context, and RAGAS requires ascore() (not score()) inside one.
def make_evaluators(scorers):

    async def answer_correctness_evaluator(*, input, output, expected_output, **kwargs):
        try:
            result = await scorers["answer_correctness"].ascore(
                user_input=input["question"],
                response=output["response"],
                reference=expected_output["reference"],
            )
            return Evaluation(name="answer_correctness", value=float(result.value))
        except Exception as e:
            print(f"   WARN: answer_correctness failed: {e}")
            # Return a score of 0.0 with a comment — Langfuse rejects None values
            return Evaluation(name="answer_correctness", value=0.0, comment=f"FAILED: {e}")

    async def context_recall_evaluator(*, input, output, expected_output, **kwargs):
        if not output["contexts"]:
            return Evaluation(name="context_recall", value=0.0, comment="No contexts retrieved")
        try:
            result = await scorers["context_recall"].ascore(
                user_input=input["question"],
                retrieved_contexts=output["contexts"],
                reference=expected_output["reference"],
            )
            return Evaluation(name="context_recall", value=float(result.value))
        except Exception as e:
            print(f"   WARN: context_recall failed: {e}")
            return Evaluation(name="context_recall", value=0.0, comment=f"FAILED: {e}")

    async def faithfulness_evaluator(*, input, output, expected_output, **kwargs):
        if not output["contexts"]:
            return Evaluation(name="faithfulness", value=0.0, comment="No contexts retrieved")
        try:
            result = await scorers["faithfulness"].ascore(
                user_input=input["question"],
                response=output["response"],
                retrieved_contexts=output["contexts"],
            )
            return Evaluation(name="faithfulness", value=float(result.value))
        except Exception as e:
            print(f"   WARN: faithfulness failed: {e}")
            return Evaluation(name="faithfulness", value=0.0, comment=f"FAILED: {e}")

    return [
        answer_correctness_evaluator,
        context_recall_evaluator,
        faithfulness_evaluator,
    ]


# ── Main ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Run a RAG experiment on Langfuse dataset"
    )
    parser.add_argument(
        "--dataset",
        choices=["sample", "full"],
        default="sample",
        help="Which Langfuse dataset to run against (default: sample)",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Experiment name (e.g. 'baseline-v1', 'chunk-256'). Must be unique per run.",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Optional description of what changed in this experiment.",
    )
    args = parser.parse_args()

    langfuse_dataset_name = LANGFUSE_DATASET_NAMES[args.dataset]

    langfuse = init_langfuse()
    scorers = init_scorers()
    evaluators = make_evaluators(scorers)

    dataset = langfuse.get_dataset(langfuse_dataset_name)

    # ── Run experiment ───────────────────────────────────
    result = dataset.run_experiment(
        name=args.name,
        description=args.description or f"RAG experiment: {args.name}",
        task=rag_task,
        evaluators=evaluators,
        metadata={
            "rag_api_url": RAG_API_URL,
            "dataset": args.dataset,
        },
    )

    langfuse.flush()
    langfuse.shutdown()


if __name__ == "__main__":
    main()