# task is to create a script, which can ingest infinitely long text-files (..)
# and give me a summarization.
# prompt should be variable: based on how i want to query the text.

from langchain.document_loaders import TextLoader

# Load text data from a file using TextLoader
loader = TextLoader("sample.txt")
document = loader.load()