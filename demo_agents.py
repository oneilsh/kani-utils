from kani_utils.base_kanis import StreamlitKani
from kani import AIParam, ai_function
import streamlit as st

from typing import Annotated
import pandas as pd
import pdfplumber
import re
import streamlit as st
from kani import AIParam, ai_function
from typing import Annotated
import pandas as pd
from pandasql import sqldf
import requests

# StreamlitKani agents are Kani agents and work the same
# We must subclass StreamlitKani instead of Kani to get the Streamlit UI
class AuthorSearchKani(StreamlitKani):
    # Be sure to override the __init__ method to pass any parameters to the superclass
    def __init__(self, *args, **kwargs):
        # if you have a system prompt, add it to the kwargs before calling super()
        kwargs["system_prompt"] = "You are a chatbot assistant that can help users find the author of a book. Always use the search_author function to find the author of a book."

        super().__init__(*args, **kwargs)

        # Define avatars for the agent and user
        # Can be URLs or emojis
        self.avatar = "📚"
        self.user_avatar = "👤"

        # The name and greeting are shown at the start of the chat
        # The greeting is not known to the LLM, it serves as a prompt for the user
        self.name = "Author Search Agent"
        self.greeting = "Hello, I'm a demo assistant. You can ask me to look up the author of a book, for example, 'Who wrote The Sorcerer's Stone?'"
        
        # The description is shown in the sidebar and provides more information about the agent
        self.description = "An agent that demonstrates the basic capabilities of Streamlit+Kani."

        # we can define any other instance variables we need for the agent
        self.search_history = []

    @ai_function()
    def search_author(self, query: Annotated[str, AIParam(desc="The query to search for.")]):
        """Search for an author and return their name and alternative names."""

        # add the search to the search history
        self.search_history.append(query)

        # use requests lib to make the GET call and parse the result
        response = requests.get(f"https://openlibrary.org/search.json?q={query}&fields=author_name,author_alternative_name&limit=1").json()
        author_name = response["docs"][0]["author_name"][0]
        alternative_names = response["docs"][0]["author_alternative_name"]

        alt_names_df = pd.DataFrame({"alternative_names": alternative_names})

        # render the response in the chat; Streamlit has nice defaults for many data types, including pandas dataframes
        self.render_in_streamlit_chat(lambda: st.write(alt_names_df))

        # the return value is sent to the agent; the user can see the response by expanding the "full context" if enabled
        return f"Author: {author_name}. Alternative names: {', '.join(alternative_names)} The user has also been shown a table of alternative names."


    ## StreamlitKanis can optionally define render_sidebar methods, which 
    ## provide the UI elements to include in the sidebar that pertain to this agent
    def render_sidebar(self):
        # Call the superclass method to render the default sidebar elements
        super().render_sidebar()
        st.divider()

        st.markdown("### Search History")
        st.caption("Previous searches:")

        # render a list of memory keys stored in markdown
        search_history = self.search_history
        # markdown-formatted list
        st.markdown("- " + "\n- ".join(search_history))



# Demonstrates adding a key/value memory store to a Kani
class MemoryKani(StreamlitKani):
    """A Kani that can store and retrieve values from memory."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.avatar = "🧠"
        self.user_avatar = "👤"

        self.name = "Memory Agent"
        self.greeting = "Hello, I'm a demo assistant. I can remember things and retrieve them later accurately."
        self.description = "An agent with key/value memory storage."

        self.memory = {}

    ## StreamlitKanis can define render_sidebar methods, which 
    ## provide the UI elements to include in the sidebar that pertain to this agent
    def render_sidebar(self):
        # Call the superclass method to render the default sidebar elements
        super().render_sidebar()
        st.divider()

        st.markdown("### Memory")
        st.caption("Key/value memories can be saved or accessed in conversation. Memory is cleared when the model is reloaded. The following keys are currently stored:")
        memory_keys = self.list_memory_keys()

        # render a list of memory keys stored in markdown
        if len(memory_keys) == 0:
            memory_keys = ["*None*"]
        sep = "\n- "
        st.markdown("- " + sep.join(memory_keys))

    @ai_function()
    def save_to_memory(self,
                       key: Annotated[str, AIParam(desc="The key to save the value under.")],
                       value: Annotated[str, AIParam(desc="The value to save.")]):
        """Save a value to memory."""
        self.memory[key] = value
        return f"Value saved under key '{key}' in memory."

    @ai_function()
    def get_from_memory(self,
                        key: Annotated[str, AIParam(desc="The key to retrieve the value for.")]):
        """Retrieve a value from memory."""
        return self.memory.get(key, None)

    @ai_function()
    def list_memory_keys(self):
        """List the keys currently stored in memory."""
        return list(self.memory.keys())
    
    @ai_function()
    def remove_from_memory(self,
                           key: Annotated[str, AIParam(desc="The key to remove.")]):
        """Remove a value from memory."""
        if key in self.memory:
            del self.memory[key]
            return f"Key '{key}' removed from memory."
        else:
            return f"Key '{key}' not found in memory."

## Uses streamlit's file handling
class FileKani(MemoryKani):
    """A Kani that can access the contents of uploaded files."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = "File Agent"
        self.greeting = "Hello, I'm a demo assistant. You can upload files and I can see their contents. I can work with text, PDF, and JSON files. Note that I do not currently implement chunking or RAG of large documents."
        self.description = "An agent that can read file contents."


        self.files = []

    def render_sidebar(self):
        super().render_sidebar()
        st.divider()

        st.markdown("### Files")
        st.caption("When referenced in conversation, uploaded text-like file contents (txt, pdf, json) will be supplied in full to the model.")
        
        # Put the file upload UI element in the sidebar - streamlit handles its state
        uploaded_files = st.file_uploader("Upload a document", 
                                          type= None, 
                                          accept_multiple_files = True,
                                          )
        
        # replace the agents files with the returned list (which will contain
        # the current file set shown in the UI)
        self.files = uploaded_files

    @ai_function()
    def get_file_contents(self, file_name: Annotated[str, AIParam(desc="The name of the file to read.")]):
        """Return the contents of the given filename as a string. If the file is not found, or is not a PDF or text-based, return None."""

        contents = None
        # self.files is managed by the file_uploader, which returns a list of uploaded files, not a dictionary
        # so we have to iterate over the list to find the file with the given name
        for file in self.files:
            if file.name == file_name:
                if file.type.startswith("text"):
                    contents = file.read()
                elif file.type == "application/pdf":
                    with pdfplumber.open(file) as pdf:
                        contents = "\n\n".join([page.extract_text() for page in pdf.pages])
                elif file.type == "application/json":
                    contents = file.read()

        if contents is None:
            return f"Error: file name not found in current uploaded file set."
        
        # convert contents to str if it is bytes
        if isinstance(contents, bytes):
            contents = contents.decode("utf-8")

        # save the contents in memory for later use
        self.memory[file_name] = contents
        message = f"Here are the contents of the file, which have also been saved in memory key '{file_name}' for further use:\n\n"
        return message + contents


    @ai_function()
    def list_current_files(self):
        """List the files currently uploaded by the user."""
        return self.files
    

class TableKani(FileKani):
    """A Kani that can run SQL queries on pandas dataframes stored in memory."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = "Tabular Data Agent"
        self.greeting = "Hello, I'm a demo assistant. You can upload files and I can see their contents. If you upload CSV files, I can read them as data frames, store them in memory, and query them like an SQL database.\n\nAlternatively, you can ask me to generate and query some example data by asking '*Please generate a set of example relational tables, save them to your local database, and run an example query on them.*'"
        self.description = "An agent that can read CSV files and query them as SQL tables."


    def render_sidebar(self):
        super().render_sidebar()
        st.divider()

        table_names = self.list_tables()
        if len(table_names) == 0:
            table_names = ["*None*"]
        sep = "\n- "
        st.markdown("### Tables")
        st.caption("Uploaded CSV files can be ingested as tables on request and later queried with SQL. The following tables are currently stored:")
        st.markdown("- " + sep.join(table_names))

    @ai_function()
    def save_to_table(self, tbl_json: Annotated[str, AIParam(desc="The JSON string to save as a table. Uses pd.read_json()")]):
        """Save a JSON string as a table in memory."""
        try:
            df = pd.read_json(tbl_json)
            table_name = f"TABLE_{len(self.memory)}"
            self.memory[table_name] = df
            return f"Table saved in memory key '{table_name}'."
        except Exception as e:
            return f"Error: {e}"

    @ai_function()
    # todo: convert to something like "load_csv_files" that takes a list of files,
    # don't display to user (make seperate visualization function)
    def read_csv_file(self, file_name: Annotated[str, AIParam(desc="The name of the file to read.")]):
        """Read a CSV file uploaded by the user."""
        for file in self.files:
            if file.name == file_name:

                # assume the file is a csv, use pandas to read it
                if file.type == "text/csv":
                    df = pd.read_csv(file)

                    # create an SQL-compatible table name based on the filename, keeping only alphanumeric characters, dots to underscores, and uppercasing
                    table_name = re.sub(r"[^a-zA-Z0-9_]", "_", file_name).upper()

                    sample = df.head(10)

                    message = f"Here is a sample of the data: {sample.to_markdown()}.\n\nThere are {len(df)} rows total, and {len(df.columns)} columns named: {', '.join(df.columns)}."
                    self.memory[table_name] = df
                    message += f"\n\nThe data has been saved in memory key '{table_name}' for further use."

                    return message

                else:
                    return f"Error: file is not a CSV."
                
        return f"Error: file name not found in current uploaded file set."


    @ai_function()
    def list_tables(self):
        """List pandas dataframes stored in memory, which can be queried and joined with SQL."""
        pandas_tables = [k for k, v in self.memory.items() if isinstance(v, pd.DataFrame)]
        return pandas_tables
   
    @ai_function()
    def run_query(self,
                 query: Annotated[str, AIParam(desc="The query to run.")],
                 save_result_to_memory_key: Annotated[str, AIParam(desc="Optional: the key to save the result to. If not provided, the result will not be saved.")] = None
                 ):
        """Query the pandas dataframes store in memory as an SQL database. Use memory key names as table names. Results are returned as text."""
        try:
            memory_dfs = {k: v for k, v in self.memory.items() if isinstance(v, pd.DataFrame)}
            result = sqldf(query, memory_dfs)

            if save_result_to_memory_key is not None:
                self.memory[save_result_to_memory_key] = result

            return result.to_string(index=False)
        except Exception as e:
            return f"Error: {e}"
