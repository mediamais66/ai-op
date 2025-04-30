import os
import re
from flask import Flask, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import google.generativeai as genai
from flask_cors import CORS
import tiktoken
from datetime import datetime
from docx import Document
import requests
import json
import PyPDF2
import pandas as pd
from bs4 import BeautifulSoup
import csv

# إعداد Flask
app = Flask(__name__)
CORS(app)

# التحقق من نوع الملف
valid_image_extensions = ['.png', '.jpg', '.jpeg']
valid_image_extensions_file_type = ['png', 'jpg', 'jpeg']
valid_doc_extensions = [
    # ملفات النصوص ومستندات Office
    '.txt', '.docx', '.docs', '.pdf', '.csv', '.xlsx', '.html', '.json',

    # قواعد البيانات
    '.sql', '.sqlite', '.db', '.bson', '.cql', '.neo4j',

    # ملفات الإعدادات والتكوين
    '.xml', '.yaml', '.yml', '.ini', '.conf', '.cfg',

    # ملفات البرمجة
    '.py', '.js', '.java', '.cpp', '.c', '.rb', '.php', '.ts', '.swift', '.go',
    '.cs', '.vb', '.scala', '.kt', '.rs', '.r', '.jl', '.pl', '.sh', '.bat', '.asm',
    '.lua', '.dart', '.erl', '.exs', '.ml', '.clj', '.fs', '.groovy', '.ps1', '.m',
    '.sas', '.sps', '.do', '.nb', '.tcl', '.ahk', '.applescript', '.vbs', '.tex',
    '.md', '.org', '.hs', '.adb', '.ads', '.for', '.f', '.f90',

    # ملفات التصميم
    '.css', '.scss', '.sass', '.less', '.styl'
]

valid_doc_extensions_file_type = [
    # ملفات النصوص ومستندات Office
    'txt', 'docx', 'docs', 'pdf', 'csv', 'xlsx', 'html', 'json',

    # قواعد البيانات
    'sql', 'sqlite', 'db', 'bson', 'cql', 'neo4j',

    # ملفات الإعدادات والتكوين
    'xml', 'yaml', 'yml', 'ini', 'conf', 'cfg',

    # ملفات البرمجة
    'py', 'js', 'java', 'cpp', 'c', 'rb', 'php', 'ts', 'swift', 'go',
    'cs', 'vb', 'scala', 'kt', 'rs', 'r', 'jl', 'pl', 'sh', 'bat', 'asm',
    'lua', 'dart', 'erl', 'exs', 'ml', 'clj', 'fs', 'groovy', 'ps1', 'm',
    'sas', 'sps', 'do', 'nb', 'tcl', 'ahk', 'applescript', 'vbs', 'tex',
    'md', 'org', 'hs', 'adb', 'ads', 'for', 'f', 'f90',

    # ملفات التصميم
    'css', 'scss', 'sass', 'less', 'styl'
]

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    filebook = data.get('filebook')
    model_app = data.get('model_app')
    selectedModel = model_app.get('selectedModel')
    selectedCompany = model_app.get('selectedCompany')
    chat_type = data.get('chat_type')
    chat_id = data.get('chat_id')

     # تحديد النسبة المئوية للتقليص (مثلاً 30%)
    reduction_percentage = 0.15

    # تقليص القيمة بـ 30%
    selectedModel["input_tokens"] = round(selectedModel["input_tokens"] * (1 - reduction_percentage))

    # استرجاع max_tokens بعد التقليص
    max_tokens = selectedModel.get("input_tokens")
    # يمكنك الآن استخدام max_tokens حسب الحاجة

    file_type = data.get('file_type')
    file_path = data.get('file_path')
    file_name = data.get('file_name')

    max_tokens = int(max_tokens)
    word_limit = 670

    if not question:  # التأكد من وجود السؤال
        return jsonify({"error": "Please enter a message"}), 400

    relevant_text = ""
    question_type = ""

    if chat_type == "chat":
        relevant_text = ""
        question_type = ""

        # حساب حالة الذاكرة
        total_tokens = calculate_tokens_for_memory(chat_id)  # استبدال هذه الدالة بحساب التوكينات المناسب
        memory_status = "Normal"  # الحالة الافتراضية
        if total_tokens > max_tokens:  # إذا كانت الذاكرة فوق الحد الأقصى
            memory_status = "Over Full"
        elif total_tokens > max_tokens * 0.8:  # 80% من الحد الأقصى
            memory_status = "Warning"
        elif total_tokens > max_tokens / 2:
            memory_status = "Normal - Memory is operating normally"
        else:
            memory_status = "Normal"
    else:
        # # التعامل مع الكتاب أو الملف المرفق
        # file_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'storage', 'books', filebook)

        # try:
        #     with open(file_path, 'r', encoding='utf-8') as file:
        #         book_content = file.read()
        # except Exception as e:
        #     return jsonify({"error": f"حدث خطأ في فتح الملف: {e}"}), 500
        file_path__ = f"storage/books/{filebook}"  # المسار النسبي للملف
        base_url = "https://hl-ai.kulshy.online"  # الرابط الأساسي للموقع

        # استدعاء الوظيفة
        book_content = fetch_and_read_file(file_path__, base_url)
        book_content = clean_text(book_content)
        question_type = analyze_question(question)
        relevant_text = retrieve_relevant_text(question, book_content, word_limit)
        memory_status = ""


    # استدعاء دالة generate_response مع النص المستخرج
    response = {
        'answer': generate_response(relevant_text, question, question_type, selectedModel, selectedCompany, chat_id, chat_type, max_tokens, files=file_path ,file_type=file_type, file_name=file_name),
        'book_piece': relevant_text,
        'question': question,
        'memory_status': memory_status # إضافة حالة الذاكرة
    }

    return jsonify({"response": response})

import os
import re
from flask import Flask, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
import google.generativeai as genai
from flask_cors import CORS
import tiktoken
from datetime import datetime
from docx import Document
import requests
import json
import PyPDF2
import pandas as pd
from bs4 import BeautifulSoup
import csv

# إعداد Flask
app = Flask(__name__)
CORS(app)

# التحقق من نوع الملف
valid_image_extensions = ['.png', '.jpg', '.jpeg']
valid_image_extensions_file_type = ['png', 'jpg', 'jpeg']
valid_doc_extensions = [
    # ملفات النصوص ومستندات Office
    '.txt', '.docx', '.docs', '.pdf', '.csv', '.xlsx', '.html', '.json',

    # قواعد البيانات
    '.sql', '.sqlite', '.db', '.bson', '.cql', '.neo4j',

    # ملفات الإعدادات والتكوين
    '.xml', '.yaml', '.yml', '.ini', '.conf', '.cfg',

    # ملفات البرمجة
    '.py', '.js', '.java', '.cpp', '.c', '.rb', '.php', '.ts', '.swift', '.go',
    '.cs', '.vb', '.scala', '.kt', '.rs', '.r', '.jl', '.pl', '.sh', '.bat', '.asm',
    '.lua', '.dart', '.erl', '.exs', '.ml', '.clj', '.fs', '.groovy', '.ps1', '.m',
    '.sas', '.sps', '.do', '.nb', '.tcl', '.ahk', '.applescript', '.vbs', '.tex',
    '.md', '.org', '.hs', '.adb', '.ads', '.for', '.f', '.f90',

    # ملفات التصميم
    '.css', '.scss', '.sass', '.less', '.styl'
]

valid_doc_extensions_file_type = [
    # ملفات النصوص ومستندات Office
    'txt', 'docx', 'docs', 'pdf', 'csv', 'xlsx', 'html', 'json',

    # قواعد البيانات
    'sql', 'sqlite', 'db', 'bson', 'cql', 'neo4j',

    # ملفات الإعدادات والتكوين
    'xml', 'yaml', 'yml', 'ini', 'conf', 'cfg',

    # ملفات البرمجة
    'py', 'js', 'java', 'cpp', 'c', 'rb', 'php', 'ts', 'swift', 'go',
    'cs', 'vb', 'scala', 'kt', 'rs', 'r', 'jl', 'pl', 'sh', 'bat', 'asm',
    'lua', 'dart', 'erl', 'exs', 'ml', 'clj', 'fs', 'groovy', 'ps1', 'm',
    'sas', 'sps', 'do', 'nb', 'tcl', 'ahk', 'applescript', 'vbs', 'tex',
    'md', 'org', 'hs', 'adb', 'ads', 'for', 'f', 'f90',

    # ملفات التصميم
    'css', 'scss', 'sass', 'less', 'styl'
]

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    filebook = data.get('filebook')
    model_app = data.get('model_app')
    selectedModel = model_app.get('selectedModel')
    selectedCompany = model_app.get('selectedCompany')
    chat_type = data.get('chat_type')
    chat_id = data.get('chat_id')

     # تحديد النسبة المئوية للتقليص (مثلاً 30%)
    reduction_percentage = 0.15

    # تقليص القيمة بـ 30%
    selectedModel["input_tokens"] = round(selectedModel["input_tokens"] * (1 - reduction_percentage))

    # استرجاع max_tokens بعد التقليص
    max_tokens = selectedModel.get("input_tokens")
    # يمكنك الآن استخدام max_tokens حسب الحاجة

    file_type = data.get('file_type')
    file_path = data.get('file_path')
    file_name = data.get('file_name')

    max_tokens = int(max_tokens)
    word_limit = 670

    if not question:  # التأكد من وجود السؤال
        return jsonify({"error": "Please enter a message"}), 400

    relevant_text = ""
    question_type = ""

    if chat_type == "chat":
        relevant_text = ""
        question_type = ""

        # حساب حالة الذاكرة
        total_tokens = calculate_tokens_for_memory(chat_id)  # استبدال هذه الدالة بحساب التوكينات المناسب
        memory_status = "Normal"  # الحالة الافتراضية
        if total_tokens > max_tokens:  # إذا كانت الذاكرة فوق الحد الأقصى
            memory_status = "Over Full"
        elif total_tokens > max_tokens * 0.8:  # 80% من الحد الأقصى
            memory_status = "Warning"
        elif total_tokens > max_tokens / 2:
            memory_status = "Normal - Memory is operating normally"
        else:
            memory_status = "Normal"
    else:
        # # التعامل مع الكتاب أو الملف المرفق
        # file_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'storage', 'books', filebook)

        # try:
        #     with open(file_path, 'r', encoding='utf-8') as file:
        #         book_content = file.read()
        # except Exception as e:
        #     return jsonify({"error": f"حدث خطأ في فتح الملف: {e}"}), 500
        file_path__ = f"storage/books/{filebook}"  # المسار النسبي للملف
        base_url = "https://hl-ai.kulshy.online"  # الرابط الأساسي للموقع

        # استدعاء الوظيفة
        book_content = fetch_and_read_file(file_path__, base_url)
        book_content = clean_text(book_content)
        question_type = analyze_question(question)
        relevant_text = retrieve_relevant_text(question, book_content, word_limit)
        memory_status = ""


    # استدعاء دالة generate_response مع النص المستخرج
    response = {
        'answer': generate_response(relevant_text, question, question_type, selectedModel, selectedCompany, chat_id, chat_type, max_tokens, files=file_path ,file_type=file_type, file_name=file_name),
        'book_piece': relevant_text,
        'question': question,
        'memory_status': memory_status # إضافة حالة الذاكرة
    }

    return jsonify({"response": response})


