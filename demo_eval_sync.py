### Kani and StreamlitKani agents return results asynchronously
### This example shows how to run a full round synchronously, which is useful for testing or debugging
### Messages are generally lists of kani.ChatMessage objects, see kani documentation for more info

# for reading API keys from .env file
import os
import dotenv # pip install python-dotenv

# kani imports
from kani.engines.openai import OpenAIEngine

# load app-defined agents
from demo_agents import AuthorSearchKani

# load utility for running a full round synchronously
from kani_utils.utils import full_round_sync

# read API keys .env file (e.g. set OPENAI_API_KEY=.... in .env and gitignore .env)
dotenv.load_dotenv() 

# define an engine to use (see Kani documentation for more info)
engine = OpenAIEngine(os.environ["OPENAI_API_KEY"], model="gpt-4o")

agent = AuthorSearchKani(engine)

print("\nAgent history initially:")
for msg in agent.chat_history:
    print(msg)

res = full_round_sync(agent, "What is the name of the author of the book 'The Great Gatsby'?")

print("\nMessages returned from first full_round_sync:")
for msg in res:
    print(msg)

print("\nAgent history after first round:")
for msg in agent.chat_history:
    print(msg)

res2 = full_round_sync(agent, "What is the name of the author of the book 'The Hobbit'?")

print("\nMessages returned from second full_round_sync:")
for msg in res2:
    print(msg)

print("\nAgent history after second round:")
for msg in agent.chat_history:
    print(msg)


## printed output:
# Agent history initially:

# Messages returned from first full_round_sync:
# role=<ChatRole.ASSISTANT: 'assistant'> content=None name=None tool_call_id=None tool_calls=[ToolCall(id='call_DRqwmXY7MTcGQEwVaOFFByut', type='function', function=FunctionCall(name='search_author', arguments='{"query":"The Great Gatsby"}'))] is_tool_call_error=None
# role=<ChatRole.FUNCTION: 'function'> content='Author: F. Scott Fitzgerald. Alternative names: SCOTT FITZGERALD FRANCIS, Francis FITZGERALD, Francis Scott Key, Fitzgerald, Scott F. Fitzgerald, F. FITZGERALD, F Fitzgerald, F>SCOT FITZGERALD, Francis-Scott Fitzgerald, Francis Scott Fitzgerald, The Great Gatsby F. Scott Fitzgerald, FRANCIS SCOTT FITZGERALD, SCOTT FITZGERALD  FR, Fitzgerald Scott F. Scott, SCOTT FITZGERALD, F. Scott Fitzgerald (author), Fitzgerald F Scott, F. Scott Fitzgerald,F Scott Fitzgerald, Fitzgerald, Frances Scott, F. -S. Fitzgerald, The Four Fists Annotated Scott Fitzgerald, Fitzgerald. Scott, F. SCOT FITZGERALD, Francis Scott Francis Scott Fitzgerald, Fitzgerald F Scott (Francis Scott), Scott Fitzgerald, Frances Scott Key Fitzgerald, F. Scott 1896-1940 Fitzgerald, Fitzgerald, Scott, F., F. Scott. Fitzgerald, F Scott Fitzgerald, F Fitzgerald Scott, F. scott fitzgerald, Mr Francis Scott Key Fitzgerald, Francis Scott Key Fitzgerald, Fitzgerald Scott, Fitzgerald Francis Scott, francis scott fitzgerald, F. Scott FITZGERALD, (mei) Feicijielade (Fitzgerald, Francis Scott, F. [Francis] Scott [Key] Fitzgerald, F. Fitzgerald, Francis Scott, Fitzgerald,, F. Scoot Fitzgerald, F. SCOTT FITZGERALD, Francis Scott FITZGERALD, Scott FITZGERALD, Fitzgerald, F. Scott. Wilson, Edmund, Fitzgerald Fitzgerald, F. Scott F. Scott Fitzgerald, The Great Gatsby Annotated Fitzgerald, F. Scott (Francis Scott) Fitzgerald, fscott Fitzgerald, F Scott 1896-1940 Fitzgerald, F. Scot Fitzgerald, A. F. Scott Fitzgerald, francis fitzgerald, F.Scott Fitzgerald, Fran Scott Fitzgerald, Fitzgerald, F. Scott, Hill, David A., f fitzgerald, F. Scott Fitzgerald Fitzgerald, Fitzgerald F. Scott, FITZGERALD FRANCIS SCOTT, F. S. Fitzgerald The user has also been shown a table of alternative names.' name='search_author' tool_call_id='call_DRqwmXY7MTcGQEwVaOFFByut' tool_calls=None is_tool_call_error=False
# role=<ChatRole.ASSISTANT: 'assistant'> content='The author of the book "The Great Gatsby" is F. Scott Fitzgerald.' name=None tool_call_id=None tool_calls=None is_tool_call_error=None

# Agent history after first round:
# role=<ChatRole.USER: 'user'> content="What is the name of the author of the book 'The Great Gatsby'?" name=None tool_call_id=None tool_calls=None is_tool_call_error=None
# role=<ChatRole.ASSISTANT: 'assistant'> content=None name=None tool_call_id=None tool_calls=[ToolCall(id='call_DRqwmXY7MTcGQEwVaOFFByut', type='function', function=FunctionCall(name='search_author', arguments='{"query":"The Great Gatsby"}'))] is_tool_call_error=None
# role=<ChatRole.FUNCTION: 'function'> content='Author: F. Scott Fitzgerald. Alternative names: SCOTT FITZGERALD FRANCIS, Francis FITZGERALD, Francis Scott Key, Fitzgerald, Scott F. Fitzgerald, F. FITZGERALD, F Fitzgerald, F>SCOT FITZGERALD, Francis-Scott Fitzgerald, Francis Scott Fitzgerald, The Great Gatsby F. Scott Fitzgerald, FRANCIS SCOTT FITZGERALD, SCOTT FITZGERALD  FR, Fitzgerald Scott F. Scott, SCOTT FITZGERALD, F. Scott Fitzgerald (author), Fitzgerald F Scott, F. Scott Fitzgerald,F Scott Fitzgerald, Fitzgerald, Frances Scott, F. -S. Fitzgerald, The Four Fists Annotated Scott Fitzgerald, Fitzgerald. Scott, F. SCOT FITZGERALD, Francis Scott Francis Scott Fitzgerald, Fitzgerald F Scott (Francis Scott), Scott Fitzgerald, Frances Scott Key Fitzgerald, F. Scott 1896-1940 Fitzgerald, Fitzgerald, Scott, F., F. Scott. Fitzgerald, F Scott Fitzgerald, F Fitzgerald Scott, F. scott fitzgerald, Mr Francis Scott Key Fitzgerald, Francis Scott Key Fitzgerald, Fitzgerald Scott, Fitzgerald Francis Scott, francis scott fitzgerald, F. Scott FITZGERALD, (mei) Feicijielade (Fitzgerald, Francis Scott, F. [Francis] Scott [Key] Fitzgerald, F. Fitzgerald, Francis Scott, Fitzgerald,, F. Scoot Fitzgerald, F. SCOTT FITZGERALD, Francis Scott FITZGERALD, Scott FITZGERALD, Fitzgerald, F. Scott. Wilson, Edmund, Fitzgerald Fitzgerald, F. Scott F. Scott Fitzgerald, The Great Gatsby Annotated Fitzgerald, F. Scott (Francis Scott) Fitzgerald, fscott Fitzgerald, F Scott 1896-1940 Fitzgerald, F. Scot Fitzgerald, A. F. Scott Fitzgerald, francis fitzgerald, F.Scott Fitzgerald, Fran Scott Fitzgerald, Fitzgerald, F. Scott, Hill, David A., f fitzgerald, F. Scott Fitzgerald Fitzgerald, Fitzgerald F. Scott, FITZGERALD FRANCIS SCOTT, F. S. Fitzgerald The user has also been shown a table of alternative names.' name='search_author' tool_call_id='call_DRqwmXY7MTcGQEwVaOFFByut' tool_calls=None is_tool_call_error=False
# role=<ChatRole.ASSISTANT: 'assistant'> content='The author of the book "The Great Gatsby" is F. Scott Fitzgerald.' name=None tool_call_id=None tool_calls=None is_tool_call_error=None

# Messages returned from second full_round_sync:
# role=<ChatRole.ASSISTANT: 'assistant'> content=None name=None tool_call_id=None tool_calls=[ToolCall(id='call_BgjXX8Mb85nSBwXGdXH1QJ51', type='function', function=FunctionCall(name='search_author', arguments='{"query":"The Hobbit"}'))] is_tool_call_error=None
# role=<ChatRole.FUNCTION: 'function'> content='Author: J.R.R. Tolkien. Alternative names: Yue Han Luo Na De Rui Er Tuo Er Jin, John R. R. Tolkien, John Ronald Reuel Tolkien, Tolkien, J R R Tolkien, J. R. R. Tolkien, J. R.R. Tolkien, J.R.R.Tolkien, Dzhon R. R. Tolkin The user has also been shown a table of alternative names.' name='search_author' tool_call_id='call_BgjXX8Mb85nSBwXGdXH1QJ51' tool_calls=None is_tool_call_error=False
# role=<ChatRole.ASSISTANT: 'assistant'> content='The author of the book "The Hobbit" is J.R.R. Tolkien.' name=None tool_call_id=None tool_calls=None is_tool_call_error=None

# Agent history after second round:
# role=<ChatRole.USER: 'user'> content="What is the name of the author of the book 'The Great Gatsby'?" name=None tool_call_id=None tool_calls=None is_tool_call_error=None
# role=<ChatRole.ASSISTANT: 'assistant'> content=None name=None tool_call_id=None tool_calls=[ToolCall(id='call_DRqwmXY7MTcGQEwVaOFFByut', type='function', function=FunctionCall(name='search_author', arguments='{"query":"The Great Gatsby"}'))] is_tool_call_error=None
# role=<ChatRole.FUNCTION: 'function'> content='Author: F. Scott Fitzgerald. Alternative names: SCOTT FITZGERALD FRANCIS, Francis FITZGERALD, Francis Scott Key, Fitzgerald, Scott F. Fitzgerald, F. FITZGERALD, F Fitzgerald, F>SCOT FITZGERALD, Francis-Scott Fitzgerald, Francis Scott Fitzgerald, The Great Gatsby F. Scott Fitzgerald, FRANCIS SCOTT FITZGERALD, SCOTT FITZGERALD  FR, Fitzgerald Scott F. Scott, SCOTT FITZGERALD, F. Scott Fitzgerald (author), Fitzgerald F Scott, F. Scott Fitzgerald,F Scott Fitzgerald, Fitzgerald, Frances Scott, F. -S. Fitzgerald, The Four Fists Annotated Scott Fitzgerald, Fitzgerald. Scott, F. SCOT FITZGERALD, Francis Scott Francis Scott Fitzgerald, Fitzgerald F Scott (Francis Scott), Scott Fitzgerald, Frances Scott Key Fitzgerald, F. Scott 1896-1940 Fitzgerald, Fitzgerald, Scott, F., F. Scott. Fitzgerald, F Scott Fitzgerald, F Fitzgerald Scott, F. scott fitzgerald, Mr Francis Scott Key Fitzgerald, Francis Scott Key Fitzgerald, Fitzgerald Scott, Fitzgerald Francis Scott, francis scott fitzgerald, F. Scott FITZGERALD, (mei) Feicijielade (Fitzgerald, Francis Scott, F. [Francis] Scott [Key] Fitzgerald, F. Fitzgerald, Francis Scott, Fitzgerald,, F. Scoot Fitzgerald, F. SCOTT FITZGERALD, Francis Scott FITZGERALD, Scott FITZGERALD, Fitzgerald, F. Scott. Wilson, Edmund, Fitzgerald Fitzgerald, F. Scott F. Scott Fitzgerald, The Great Gatsby Annotated Fitzgerald, F. Scott (Francis Scott) Fitzgerald, fscott Fitzgerald, F Scott 1896-1940 Fitzgerald, F. Scot Fitzgerald, A. F. Scott Fitzgerald, francis fitzgerald, F.Scott Fitzgerald, Fran Scott Fitzgerald, Fitzgerald, F. Scott, Hill, David A., f fitzgerald, F. Scott Fitzgerald Fitzgerald, Fitzgerald F. Scott, FITZGERALD FRANCIS SCOTT, F. S. Fitzgerald The user has also been shown a table of alternative names.' name='search_author' tool_call_id='call_DRqwmXY7MTcGQEwVaOFFByut' tool_calls=None is_tool_call_error=False
# role=<ChatRole.ASSISTANT: 'assistant'> content='The author of the book "The Great Gatsby" is F. Scott Fitzgerald.' name=None tool_call_id=None tool_calls=None is_tool_call_error=None
# role=<ChatRole.USER: 'user'> content="What is the name of the author of the book 'The Hobbit'?" name=None tool_call_id=None tool_calls=None is_tool_call_error=None
# role=<ChatRole.ASSISTANT: 'assistant'> content=None name=None tool_call_id=None tool_calls=[ToolCall(id='call_BgjXX8Mb85nSBwXGdXH1QJ51', type='function', function=FunctionCall(name='search_author', arguments='{"query":"The Hobbit"}'))] is_tool_call_error=None
# role=<ChatRole.FUNCTION: 'function'> content='Author: J.R.R. Tolkien. Alternative names: Yue Han Luo Na De Rui Er Tuo Er Jin, John R. R. Tolkien, John Ronald Reuel Tolkien, Tolkien, J R R Tolkien, J. R. R. Tolkien, J. R.R. Tolkien, J.R.R.Tolkien, Dzhon R. R. Tolkin The user has also been shown a table of alternative names.' name='search_author' tool_call_id='call_BgjXX8Mb85nSBwXGdXH1QJ51' tool_calls=None is_tool_call_error=False
# role=<ChatRole.ASSISTANT: 'assistant'> content='The author of the book "The Hobbit" is J.R.R. Tolkien.' name=None tool_call_id=None tool_calls=None is_tool_call_error=None
