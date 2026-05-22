from dotenv import load_dotenv

load_dotenv()

from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings as LCOpenAIEmbeddings
from langchain_community.document_loaders.parsers import LLMImageBlobParser
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from ragas.testset import TestsetGenerator
import os

if __name__ == "__main__":
    file_path = "./documents/TXManualExtract.pdf"
    image_parser = LLMImageBlobParser(
        model=ChatOpenAI(model="gpt-4.1-mini", max_tokens=1024)
    )
    loader = PyMuPDF4LLMLoader(
        file_path,
        mode="single",
        pages_delimiter="----END OF PAGE----",
        extract_images=True,
        images_parser=image_parser,
        table_strategy="lines",
    )
    docs = loader.load()

    generator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-5-nano"))
    generator_embeddings = LangchainEmbeddingsWrapper(LCOpenAIEmbeddings())

    generator = TestsetGenerator(
        llm=generator_llm, embedding_model=generator_embeddings
    )
    dataset = generator.generate_with_langchain_docs(docs, testset_size=50)
    df = dataset.to_pandas()
    os.makedirs("evals/datasets", exist_ok=True)
    df.to_csv("evals/datasets/testset.csv", index=False)
