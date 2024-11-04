api_key = "AIzaSyB3TMqSkUk6Z5iCYOy5KttwbsMdqt7OK60"


import getpass
import os

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = api_key


import re
import os
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

# Set up environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("GOOGLE_API_KEY is not set in environment variables.")
    st.stop()

# Database connection
mysql_uri = 'mysql+mysqlconnector://root:fernando88@localhost:3308/chinook'
db = SQLDatabase.from_uri(mysql_uri)

# SQL and response prompt templates
template_sql = """Based on the table schema below, write only the SQL query to answer the user's question:
{schema}

Question: {question}
SQL Query (no extra formatting):"""
prompt_sql = ChatPromptTemplate.from_template(template_sql)

template_response = """Based on the table schema below, question, sql query, and sql response, write a natural language response:
{schema}

Question: {question}
SQL Query: {query}
SQL Response: {response}"""
prompt_response = ChatPromptTemplate.from_template(template_response)

# Define helper functions
def get_schema():
    try:
        schema = db.get_table_info()
        if not schema:
            raise ValueError("Schema information is empty.")
        return schema
    except Exception as e:
        st.error(f"Error fetching schema: {e}")
        return ""

def run_query(query):
    try:
        result = db.run(query)
        return result
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

# Initialize language model
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

sql_chain = prompt_sql | llm.bind(stop=["\nSQLResult:"]) | StrOutputParser()

# Streamlit UI
st.title("SQL Query Generator and Natural Language Responder")
user_question = st.text_input("Enter your question about the database:")

if st.button("Generate Query and Response"):
    if user_question:
        schema = get_schema()
        raw_sql_query = sql_chain.invoke({"schema": schema, "question": user_question})
        sql_query = re.sub(r"```(?:sql)?|```", "", raw_sql_query).strip()
        
        st.subheader("Generated SQL Query")
        st.code(sql_query, language='sql')
        
        sql_response = run_query(sql_query)
        
        if sql_response:
            response_data = {
                "schema": schema,
                "question": user_question,
                "query": sql_query,
                "response": sql_response
            }
            final_result = llm.invoke(prompt_response.format(**response_data))
            
            st.subheader("Natural Language Response")
            st.write(final_result.content)
        else:
            st.error("Failed to retrieve SQL response.")
    else:
        st.warning("Please enter a question to proceed.")
