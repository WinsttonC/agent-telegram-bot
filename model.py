from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.prompts import MessagesPlaceholder
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import AgentTokenBufferMemory
from langchain.agents import AgentExecutor
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma


from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.schema.messages import HumanMessage, AIMessage

from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type
from docx import Document
import re 
from docxtpl import DocxTemplate
from collections import OrderedDict
        
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_module import *
from datetime import datetime

db_url = "sqlite:///main_database.db"
engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

def log_request(username, human_input, ai_output, status, timestamp=datetime.now()):
    new_log = Logs(username=username, human_input=human_input, ai_output=ai_output, timestamp=timestamp)
    session.add(new_log)
    session.commit()
    
class ModelGPT:
    def __init__(self, config):
        self.username = config.get('username')
        self.OPENAI_API_KEY = config.get('open_ai_key')
        self.memory_key = "history",
        self.syst_message_content = True,
        self.temperature = config.get('temperature')
        self.temperature = 0
        self.model = config.get('model')
        self.document_path = config.get('document_path')
        
        if config.get('chat_history') is None:
            self.chat_history = []
            AgentTokenBufferMemory.buffer = []
        else:
            self.chat_history = config.get('chat_history')
            AgentTokenBufferMemory.buffer = self.chat_history

        
        self.file_path = config.get('file_path', False)        
        self.tools = config.get('tools', False)        
        self.llm = ChatOpenAI(temperature=self.temperature, model=self.model, openai_api_key=self.OPENAI_API_KEY)
        
        self.system_message = SystemMessage(content=(
                "You are a powerful AI assistant in a company, your name is TEST GPT"
                "In your answers, be polite and, most importantly, brief. If you cannot answer question, RETURN that you cannot execute it"
                "Feel free to use the following tools: {self.tools}"
                "Answer only on behalf of the company and do not go beyond the information you have"
                "You are good at Python"
                "When you answering using a tool, rely on what the function returns"
            )
        )
        
        self.prompt = OpenAIFunctionsAgent.create_prompt(
            system_message=self.system_message,
            extra_prompt_messages=[MessagesPlaceholder(variable_name="history")]
        )


        self.agent = OpenAIFunctionsAgent(llm=self.llm, tools=self.tools, prompt=self.prompt)
        
        self.memory = AgentTokenBufferMemory(memory_key="history", llm=self.llm)
        
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            memory=self.memory, 
            verbose=True,
            return_intermediate_steps=True
        )
    
        
    def run(self, message):
        try:  
            result = self.agent_executor(message)
            log_request(username=self.username, human_input=result['input'], ai_output=result['output'], status='OK')
            return result['output']
        except Exception as e:
            error_message = f"Something went wrong! Error: {str(e)}"
            return error_message
          
class RetrieverToolInput(BaseModel):
    query : str = Field()

class RetrieverTool(BaseTool):
    name = "searching_company_information"
    description = "useful for when you need to answer questions about the company"
    args_schema: Type[BaseModel] = RetrieverToolInput

    def _run(self, query):
        vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=OpenAIEmbeddings())
        retriever = vectorstore.as_retriever()
        
        retriever_tool = create_retriever_tool(
            retriever, 
            "searching_company_information",
            "Searches and returns information about the company, its internal regulations, etc."
        ) 
        return retriever_tool.run(query)

def get_true_tools(username):
    user = session.query(Tools).filter(Tools.username == username).first()
    if not user:
        return "No user found"
    
    true_tools = []
    for tool in ['doc_retriever', 'docs_template', 'google_calendar']:
        if getattr(user, tool):
            true_tools.append(tool)

    return true_tools

def history_generation(logs):
    human_input = [log.human_input for log in logs]
    ai_output = [log.ai_output for log in logs]
    output_list = []
    
    for human_input, ai_output in zip(human_input, ai_output):
        output_list += [HumanMessage(content=human_input), AIMessage(content=ai_output)]
    return output_list

def generate_config(username):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    db_user_information = session.query(UserInformation).filter(UserInformation.username == username).all()
    db_logs = session.query(Logs).filter(Logs.username == username).all()
    db_main = session.query(MainInfo).filter(MainInfo.id == 1).first()
    db_tools = session.query(Tools).filter(Tools.username == username).first()
    
    session.close()
    
    config = {
        "username" : username,
        "open_ai_key" : db_main.open_ai_key,
        "model": db_main.model,
        "memory_key" : "history",
        "tools" : [GetNameTemplate(), InsertValuesIntoDocx()],
        "document_path" : "doc_retriever/napoleonINFO.md",
        "chat_history" : history_generation(db_logs)
    }
    
    return config

class DocumentFiller:
        
    def __init__(self, template_descr):
       
        template_paths = {
            "Шаблон заявления для оформления оплачиваемого отпуска": "./docs_templates/Заявление на отпуск.docx",
            "Шаблон заявления для оформления отпуска за свой счет" : "./docs_templates/Заявление на отпуск без сохр.docx",
        }   
        
        self.template_path = template_paths.get(template_descr)   
    
    def extract_values_from_template(self):
        
        doc = Document(self.template_path)
        
        values = []
        
        for para in doc.paragraphs:
            text = para.text
            placeholders = re.findall(r'{{\s*(.*?)\s*}}', text)
            values.extend(placeholders)

        return list(OrderedDict.fromkeys(values)) 
    
    def insert_values_into_docx(self, args : list):
        """ 
        This function insert values into docx template and returns the docx.
        """
        template_values = self.extract_values_from_template()
        
        context = {}
        for idx in range(len(template_values)):
            try:
                context[template_values[idx]] = args[idx]
            except:
                context[template_values[idx]] = '###'
        # return context
        doc = DocxTemplate(self.template_path)
        doc.render(context)
        doc.save("Документ.docx")
        return True    

template_paths = {
            "Шаблон заявления для оформления оплачиваемого отпуска": "./docs_templates/Заявление на отпуск.docx",
            "Шаблон заявления для оформления отпуска за свой счет" : "./docs_templates/Заявление на отпуск без сохр.docx",
        }      
    
class GetNameTemplateInput(BaseModel):
    query : str = Field(f"{template_paths.keys()}")
    
class GetNameTemplate(BaseTool):
    name = "get_appropriate_template"
    description = "Use this tool when you need to get the path to the corresponding document template. Return only path and run insert_values_into_docx"
    args_schema: Type[BaseModel] = GetNameTemplateInput   
    
    def _run(self, query):
        return query
               
class InsertValuesIntoDocxInput(BaseModel):
    query : str = Field()
    args: list = Field()
    
class InsertValuesIntoDocx(GetNameTemplateInput, BaseTool):
    name = "insert_values_into_docx"
    description = """
                Use this tool when you need to insert values into docx template and return a filled document based on provided args. 
                Firstly run get_appropriate_template and then insert_values_into_docx
                If you need to get info by individual taxpayer number use function get_values_by_INN
                """
    args_schema: Type[BaseModel] = InsertValuesIntoDocxInput
    
    def _run(self, query, args):
        docs = DocumentFiller(query)
        return docs.insert_values_into_docx(args)