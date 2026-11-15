# AI Tool Usage Record

Popparit Promwungkwa · Part 1: ChatGPT · Part 2: Claude

## Part 1 — ChatGPT (AI Board Game Assistant: Coup)

### Log 01: Requirements Clarification

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยวางโครงสรางเว็บไซต AI Board Game Assistant ที่คนหาบอรดเกมไดหลายเกม และแสดงกฎของเกมที่ผูใชเลือก โดยมี AI Tutor, Practice และ Learning Progress”

**PROMPT (ENGLISH GLOSS)** *“Help define the structure of a multi-game AI Board Game Assistant that allows users to search for board games, view the rules of a* *selected game, ask questions through an AI Tutor, practice with simulated scenarios, and track learning progress.”* **OUTPUT RECEIVED** A proposed application structure consisting of a home page, board game search, game-specific information, an AI Tutor, practice scenarios, and a learning progress section. **VERIFIED AGAINST** The intended project scope and the application's planned user workflow. **EDITS MADE** The application concept was clarified as a multi-game platform rather than a website dedicated exclusively to Coup. Coup was retained as the first game implemented in the prototype, while other games were presented as future extensions.

### Log 02: User Interface Design

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยออกแบบ UI ใหมใหเป็นหนาแรกสําหรับคนหาบอรดเกม และคอยแสดงกฎของเกมหลังจากผูใชเลือกเกม โดยมีเมนูเปลี่ยนภาษาไทยและ อังกฤษ”

**PROMPT (ENGLISH GLOSS)** *“Redesign the user interface around a searchable board game home page. Display game-specific rules and learning features after the* *user selects a game, and include a Thai-English language switch.”* **OUTPUT RECEIVED** A proposed Streamlit layout with a search field, game cards, game details, navigation tabs, and language settings. **VERIFIED AGAINST** The intended navigation flow and the requirement for Thai and English support. **EDITS MADE** The UI structure was adapted to the existing Streamlit application. Game cards were associated with individual game entries, and the language selection was designed to update the interface text.

-- page 1 --

### Log 03: Python and Streamlit Development

**PROMPT (AS USED, THAI)**

“ชวยตรวจสอบและปรับปรุงโคด app.py สําหรับหนาแรก การคนหาเกม เมนูกฎเกม AI Tutor Practice และ Learning Progress”

**PROMPT (ENGLISH GLOSS)** *“Review and improve the Streamlit app.py code for the home page, game search, game rules, AI Tutor, practice scenarios, and learning* *progress.”* **OUTPUT RECEIVED** Suggested Python code for page configuration, session state, language dictionaries, game listings, tabs, and interactive components. **VERIFIED AGAINST** Python syntax, Streamlit component usage, session state behavior, and the application's intended navigation. **EDITS MADE** The code was organized into sections for configuration, translations, game data, RAG integration, and the main interface. Debugging was still necessary where indentation, variable names, and function calls did not match across files.

### Log 04: Bilingual Interface

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยทําเมนูเปลี่ยนภาษาไทยและอังกฤษ และใหขอความในแตละหนาสลับตามภาษาที่เลือก”

**PROMPT (ENGLISH GLOSS)** *“Implement a Thai-English language selector and ensure that the interface text changes according to the selected language.”* **OUTPUT RECEIVED** A translation dictionary and a proposed language-selection mechanism using Streamlit session state. **VERIFIED AGAINST** The available translation keys and the behavior of the language selector. **EDITS MADE** Interface labels were organized into Thai and English dictionaries. Missing keys and incorrect language references needed to be checked to prevent runtime errors.

### Log 05: Knowledge Base Preparation

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยออกแบบโครงสราง Knowledge Base สําหรับกฎเกม Coup ในรูปแบบ JSON เพื่อใชแสดงกฎและคนหาขอมูลที่เกี่ยวของกับคําถามของผู เลน”

**PROMPT (ENGLISH GLOSS)** *“Help design a JSON knowledge base for Coup rules that can display game rules and retrieve information relevant to players' questions.”* **OUTPUT RECEIVED** A proposed structured rule format containing rule identifiers, topics, rule descriptions, and keywords. **VERIFIED AGAINST** The project's JSON structure and the authoritative rules available for the game. **EDITS MADE** The rule data was organized for programmatic retrieval. Game rules and numerical values must be checked against a reliable rulebook before being treated as authoritative.

-- page 2 --

### Log 06: Retrieval-Augmented Generation (RAG)

“ชวยตรวจสอบ rag.py ใหคนหากฎที่เกี่ยวของจาก Knowledge Base ดวย semantic search แลวสงบริบทให Ollama สรางคําตอบภาษาเดียว กับคําถามของผูใช พรอมสงคืนแหลงขอมูล RAG”

**PROMPT (ENGLISH GLOSS)** *“Review rag.py so that it retrieves relevant rules from the knowledge base using semantic search, passes the retrieved context to Ollama,* *generates an answer in the user's language, and returns the supporting RAG sources.”* **OUTPUT RECEIVED** A proposed RAG pipeline involving knowledge base loading, embedding generation, semantic similarity search, prompt construction, local language model inference, and source reporting. **VERIFIED AGAINST** The expected input and output of the RAG functions, the installed Python packages, the Ollama model name, and the actual response returned by the local model. **EDITS MADE** The RAG logic was separated from the Streamlit interface. The application was intended to receive an answer and a list of retrieved sources. Function signatures and return values needed to remain consistent between app.py and rag.py.

### Log 07: AI Tutor Integration

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยเชื่อม AI Tutor ใน app.py กับฟังกชัน ask_ai จาก rag.py ใหแสดงทัง้คําอธิบายจาก AI และ RAG Sources โดยไมทําใหหนาเว็บหยุด ทํางานเมื่อเกิดขอผิดพลาด”

**PROMPT (ENGLISH GLOSS)** *“Connect the AI Tutor in app.py to the ask_ai function in rag.py so that it displays both the AI-generated explanation and the RAG* *sources, while handling errors without crashing the application.”* **OUTPUT RECEIVED** Suggested integration code using function imports, exception handling, a loading indicator, chat history, and source expanders. **VERIFIED AGAINST** The actual function signature, the returned data structure, the availability of the Ollama service, and the rendered chat response. **EDITS MADE** The integration needed to use consistent function names and arguments. Error messages were used to identify problems involving undefined functions, incorrect variables, indentation, and model invocation.

-- page 3 --

### Log 08: Debugging and Error Analysis

“ชวยวิเคราะหและแกขอผิดพลาดที่เกิดขึน้ใน app.py และ rag.py เชน IndentationError, NameError, KeyError และปัญหาที่ AI Tutor ไม สามารถสรางคําตอบได”

**PROMPT (ENGLISH GLOSS)** *“Analyze and help resolve errors in app.py and rag.py, including IndentationError, NameError, KeyError, and failures in generating AI* *Tutor responses.”* **OUTPUT RECEIVED** Explanations of common Python errors and suggested corrections involving indentation, variable definitions, translation dictionary keys, function calls, and exception handling. **VERIFIED AGAINST** The traceback shown by Streamlit, the relevant source code, and whether the application ran successfully after each change. **EDITS MADE** Code sections were reviewed to align indentation levels and variable names. Further testing was required after changes because correcting one error did not guarantee that the complete application worked correctly.

### Log 09: Local Language Model Configuration

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยตรวจสอบการเรียกใช Ollama และโมเดลภาษาทองถิ่นสําหรับ AI Tutor รวมถึงการตัง้คา timeout และจํานวน token ที่ใชสรางคําตอบ”

**PROMPT (ENGLISH GLOSS)** *“Review the Ollama integration and local language model configuration for the AI Tutor, including timeout settings and the number of* *tokens used to generate responses.”* **OUTPUT RECEIVED** Suggestions for checking the Ollama service, model availability, request parameters, response extraction, and error handling. **VERIFIED AGAINST** The locally installed Ollama model, the service's actual response, and the application's measured response time. **EDITS MADE** The model name and API usage needed to match the installed environment. Response-time improvements were to be evaluated through actual tests rather than assumed from configuration changes.

-- page 4 --

### Log 10: Practice and Learning Progress

“ชวยสรางสถานการณฝึกฝนกฎเกม Coup พรอมตัวเลือกคําตอบ ตรวจคําตอบ และแสดงคะแนนความถูกตองในหนา Learning Progress”

*“Create Coup practice scenarios with answer choices, answer checking, and accuracy scores displayed on the Learning Progress page.”* **OUTPUT RECEIVED** A proposed practice-question data structure and Streamlit controls for answer selection and score calculation. **VERIFIED AGAINST** The game rules, the correct answer for each scenario, the answer-index mapping, and the score calculation. **EDITS MADE** Practice questions were structured as reusable data. Scoring needed to be checked to ensure that the displayed accuracy reflected submitted answers and did not incorrectly imply mastery based on unsubmitted or unreviewed work.

### Log 11: Documentation and AI Usage Reporting

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยจัดทํา AI Usage Log เป็นภาษาอังกฤษตามรูปแบบ Tool Used, Prompt, Output Received, Verified Against และ Edits Made เพื่อบันทึก การใช AI ในการพัฒนาโครงงาน”

**PROMPT (ENGLISH GLOSS)** *“Prepare an English AI Usage Log using the fields Tool Used, Prompt, Output Received, Verified Against, and Edits Made to document* *AI assistance during project development.”* **OUTPUT RECEIVED** A structured AI usage log describing the purpose of each AI-assisted development activity, its output, verification method, and subsequent changes. **VERIFIED AGAINST** The actual prompts used, available code, project requirements, observed errors, and tests that were genuinely performed. **EDITS MADE** The log should be revised to reflect the real development history. Unverified test results and AI-generated suggestions must not be reported as confirmed achievements.

-- page 5 --

### Log 12: AI Preparation for Anticipated Questions

“ชวยเทรน AI เพิ่มใหหนอยเพื่อเตรียมพรอมสําหรับการตอบคําถามที่อาจจะเจอ ขอใหพรอมมากที่สุด”

*“Please train the AI further so that it is prepared for the questions it may encounter. Make it as ready as possible.”* **OUTPUT RECEIVED** ChatGPT reported that it improved readiness by adding retrieval data and adjusting the answering behavior, and that it had not retrained the model weights. It added 105 example questions covering all 6 games, limited citations to the evidence the system actually retrieved, and reported that on 35 separate test questions the expected topic was found more often (19 to 28). It also noted that the backend had to be restarted to use the new code, and that the retrieval data had been saved and backed up. **VERIFIED AGAINST** ChatGPT's reported checks: 35 separate test questions, code and web page tests that passed 107 items, and six trials with the real model (4 answered, 1 partly answered, 1 timed out). ChatGPT therefore stated that it could not guarantee an answer to every question. These figures are as reported by ChatGPT in the chat. **EDITS MADE** ChatGPT reported editing 16 files (+409 -12), including backend/rule_assistant.py and backend/semantic_search.py. The AI is not trained in the strict sense; the change is additional example data and adjusted answering and retrieval logic.

### Log 13: Deploying the Updated Code

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“จัดการเลย”

**PROMPT (ENGLISH GLOSS)** *“Go ahead.”* **OUTPUT RECEIVED** ChatGPT reported that it put the latest code into use by restarting the backend while keeping the existing administrator password. It then checked the data through the real API for all 6 games, ran the real model after the restart, and confirmed that the web page and services were ready. The user was told to open the BoardGameTutor page, press Ctrl+F5, and log in to the admin page again with the same password. **VERIFIED AGAINST** The data returned by the API for all 6 games and a real model response after the restart, as reported by ChatGPT. ChatGPT also stated that some questions could still be slow or time out. **EDITS MADE** ChatGPT reported editing Doc/AI_PREPARATION_2026-11-09.md (+3 -1) to record the change.

-- page 6 --

### Log 14: Review of a Confusing AI Response

“คิดวายังไง รูสึกอานแลวงงไหม” (สงภาพหนาจอการสนทนาของระบบมาดวย)

*“What do you think? Does it feel confusing to read?” (A screenshot of the system's chat was attached.)* **OUTPUT RECEIVED** ChatGPT agreed that the response was confusing. The user had asked whether it is allowed to say nothing at all, but the system answered a different question about continuing to speak after losing a word. ChatGPT listed the causes: it was unclear whether the system understood the latest question, old question-and-answer pairs were repeated, the “cannot verify yet” message was long and written in system language, and the user waited 81 seconds. It suggested a short clarifying answer instead, and said the layout of the references was readable but that follow-up handling when the answer cannot be verified still needed improvement. **VERIFIED AGAINST** The attached screenshot of the chat compared with the question that was actually asked. **EDITS MADE** No code was changed in this exchange. It was used to identify what needed to be fixed in the next step.

### Log 15: General Improvement of Follow-up Handling

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“สามารถแกใหดีขึน้ตามที่คิดมาใหไดไหม แบบ ไมใชเพราะคําถามนี้”

**PROMPT (ENGLISH GLOSS)** *“Can you improve it according to what you thought, but not just for this one question?”* **OUTPUT RECEIVED** ChatGPT reported a general mechanism for all games rather than an answer for that single question. It separates the points of a question (the action, the penalty or refusal, and the timing before answering), asks a short clarifying question when the question is ambiguous, does not repeat old answers when something cannot be verified, and folds the references so they are easier to read, including the display of older chats. It was deployed, and the user was told to press Ctrl+F5. **VERIFIED AGAINST** ChatGPT reported that the tests passed 119 items and that it ran the real API. It also stated that the model still could not verify the answer for some situations. **EDITS MADE** ChatGPT reported editing 24 files (+390 -50), including backend/rule_assistant.py (+49 -1), backend/app.py (+15 -7), and Code/index.html (+10 -3).

-- page 7 --

### Log 16: Starting the Web Application

“รันใหหนอย”

*“Please run it.”* **OUTPUT RECEIVED** ChatGPT reported that the web system, the backend, and the AI were opened and ready to use, and provided a link to the BoardGameTutor page. **VERIFIED AGAINST** ChatGPT's statement that the services were running. No separate test result was shown in this exchange. **EDITS MADE** No code was changed in this exchange.

### Log 17: Fixing a Short Count Question

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

(สงภาพหนาจอการสนทนาของระบบโดยไมมีขอความ)

**PROMPT (ENGLISH GLOSS)** *(A screenshot of the system's chat was sent without any text.)* **OUTPUT RECEIVED** ChatGPT tried the sequence of questions shown in the screenshot on the real web page. After asking how many guesses are allowed when time runs out and then whether two are allowed, the system answered that it is not allowed because the rule gives one guess per round, with a reference shown immediately and a response time of 0.0 seconds. ChatGPT said the fix is a general mechanism for short questions about numbers, tested across games, and not an answer added for this one question. The page was opened and reloaded. **VERIFIED AGAINST** The question sequence from the screenshot on the real web page and across other games, as reported by ChatGPT. **EDITS MADE** ChatGPT reported editing 8 files (+174 -13), including backend/app.py and backend/rule_assistant.py.

-- page 8 --

### Log 18: Rule Retrieval and Answer Checking

(สงภาพหนาจอการสนทนาของระบบโดยไมมีขอความ)

*(A screenshot of the system's chat was sent without any text.)* **OUTPUT RECEIVED** ChatGPT reported tuning rule retrieval and answer checking together for all games and deploying the result. The question in the screenshot now returned the answer that Attack can be used to continue, with supporting evidence. It reported that the latest verification round took 26 seconds and that asking the same question again took 0.004 seconds, and warned that some new questions might still take tens of seconds. **VERIFIED AGAINST** The question in the screenshot on the running system, and the response times reported by ChatGPT. **EDITS MADE** ChatGPT reported editing 38 files (+502 -34), including backend/app.py and backend/rule_assistant.py.

### Log 19: Installing on a Friend's Computer

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“โอเค เทรนประมาณนี้ แลวจะเอาไปลงเครื่องเพื่อนไดยังไง”

**PROMPT (ENGLISH GLOSS)** *“Okay, that is about enough training. How can I install it on my friend's computer?”* **OUTPUT RECEIVED** ChatGPT packaged the latest version as a ZIP file of about 32 MB containing the code and the knowledge base, and gave Windows steps: install the Python install manager and Ollama and open Ollama; extract the ZIP and open PowerShell in the BoardGameTutor folder; run the commands to install Python 3.14, create a virtual environment, and install backend\requirements.txt; pull the models qwen3.5:4b, embeddinggemma, and qwen3:1.7b with Ollama; then double-click Start-BoardGameTutor.cmd, set the administrator password, and open the web page. It noted that the knowledge base does not need to be prepared again, that the model files are several GB and download the first time, and that the speed depends on the friend's computer. The ZIP also includes INSTALL_WINDOWS.md. **VERIFIED AGAINST** ChatGPT reported that it checked a newly extracted copy of the files and that the 21 saved answers it had checked still worked. The installation steps themselves were not run on another computer in this chat. **EDITS MADE** ChatGPT reported editing 7 files (+141 -3), including Doc/INSTALL_WINDOWS.md (+57), Start-BoardGameTutor.cmd (+4), and scripts/Start-Presentation.ps1 (+2).

-- page 9 --

### Log 20: Updating an Already Installed Computer

“ขอวิธียายหนอย สงใหเพื่อนคนเดิมที่ทําครัง้ที่แลว” และ “สงแคไฟล zip รุนลาสุดใหใชไหม”

*“Please give me the transfer steps to send to the same friend as last time.” and “Do I only send the latest ZIP file?”* **OUTPUT RECEIVED** For a computer that already has the system installed, ChatGPT explained an update method that normally needs no new Python, Ollama, or model downloads: send only the latest ZIP file; close the old system; rename the existing BoardGameTutor folder to BoardGameTutor- old; extract the new ZIP as a new BoardGameTutor folder in the same place; double-click Start-BoardGameTutor.cmd and set the administrator password if asked; then open the web page and press Ctrl+F5. If a library is missing, run the virtual environment and pip install commands again. It advised not to delete the old folder right away, because the new package uses the latest data from the user's own computer and does not include any games or data the friend added. It confirmed that sending only the latest ZIP is enough, since it contains the code, knowledge base, and installation guide. **VERIFIED AGAINST** ChatGPT's description of the package contents. The update steps were not tested on the friend's computer in this chat. **EDITS MADE** No code was changed in this exchange.

-- page 10 --

### Log 21: Project Overview and Locating the Add-Game Feature

“โปรเจคนี้เกี่ยวกับอะไร”, “ตอนนี้การเพิ่มเกมอยูตรงไหน” และ “อยูสวนไหนของ code”

*“What is this project about?”, “Where is the add-game feature at the moment?” and “Which part of the code is it in?”* **OUTPUT RECEIVED** ChatGPT described the project as BoardGameTutor, a Thai-language web application that helps people learn how to play board games, from studying the rules to testing their understanding. Its main features are game search with player count, playing time, and difficulty; step-by-step lessons, scenario practice, and quizzes with answers; an AI rule assistant that retrieves game content and uses a model through Ollama to phrase the answer; learning progress and history; and an admin page for adding games, lessons, rules, and quizzes, including importing a PDF manual so the AI can prepare a draft before it is reviewed and published. The front end is HTML/CSS/JavaScript in index.html, and the back end is Python FastAPI with SQLite in app.py. For adding games, ChatGPT explained that the admin logs in with the password set in BGT_ADMIN_PASSWORD and can either create a draft with AI (game name plus a PDF manual or pasted rules) or add a game manually, and that a new game stays a draft until it is verified and published. It then pointed to the admin page at line 1077 of index.html, the forms at lines 1082 and 1084, the ag() function at line 1088 that calls commitGame(), and the PUT /api/games/{game_id} route at line 440 of app.py. **VERIFIED AGAINST** The project files, as read by ChatGPT, which cited file names and line numbers. The line numbers were not separately checked in this record. **EDITS MADE** No code was changed in this exchange.

### Log 22: Data Storage and Running on Another Computer

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ตอนนี้ขอมูลที่บันทึกลง Database จะอยูในเครื่องนี้อยางเดียวใชไหม” และ “ไมตองใชขอมูลรวมกัน แตสามารถนําไปรันในเครื่องอื่นได”

**PROMPT (ENGLISH GLOSS)** *“Is the data saved to the database stored only on this computer?” and “We do not need shared data, but can it be run on another* *computer?”* **OUTPUT RECEIVED** ChatGPT confirmed that the database is a SQLite file (backend/data/games.sqlite3) on the computer that runs the backend, so there is no automatic syncing or cloud backup. Sharing data between several computers would require putting the backend and database on a server. A page opened without the backend, for example on GitHub Pages, uses the browser's own storage instead of SQLite. For running on another computer, ChatGPT explained that each computer keeps its own database, and that a new computer needs Python, the dependencies, the backend and the web page started as described in the README, plus Ollama and its models if the AI is used. Data can be moved in two ways: start fresh by copying the project and importing the sample games from the admin page, or copy backend/data/games.sqlite3 to the same location on the new computer after closing the backend. **VERIFIED AGAINST** ChatGPT's reading of the project's database configuration and README, as described in the chat. **EDITS MADE** No code was changed in this exchange.

-- page 11 --

### Log 23: Flow of Uploading a Game from a PDF

“ชวยบอก flow การทํางานของการอัปโหลดเกมผาน PDF ใหหนอย”

*“Please explain the workflow of uploading a game through a PDF.”* **OUTPUT RECEIVED** ChatGPT described the flow as: upload the PDF, check the text, let the AI create the game data, check the draft, save, and publish. (1) The admin enters the game name and chooses a PDF, handled by generateGameDraftFromPdf() at line 1016. (2) The page sends the file with the admin token to POST /api/admin/extract-pdf-text; the backend checks that it is a real PDF of at most 20 MB and 200 pages without a password, and extracts the text page by page with PdfReader. (3) Some Thai character errors are fixed by written rules and the text is shown in an editable box; this step does not use AI, and scanned PDFs are not supported because there is no OCR yet. (4) “Create draft from this text” sends the game name and checked text to POST /api/admin/generate-game, where the Ollama model qwen3:1.7b produces Thai structured data (description, players, time, category, difficulty, rules, lessons, practice scenarios, and quizzes with answers), and the backend validates the JSON. (5) The admin reviews and edits the JSON; nothing is saved yet. (6) “Save as draft” checks required fields, duplicate IDs, and answer options, sets pub = 0, and calls commitGame() to save to SQLite; the database stores the game as JSON, not the original PDF. (7) “Verify and publish” sets pub = 1, saves again, and makes the game visible to learners; published content becomes the knowledge base of the AI assistant. ChatGPT also noted a separate /api/admin/generate-game-from-pdf route that the current page does not use, so that the admin can check the text before it is sent to the AI. **VERIFIED AGAINST** The project's page and back-end code as read by ChatGPT, which cited function names and line numbers for each step. These were not separately checked in this record. **EDITS MADE** No code was changed in this exchange.

### Log 24: Fixing the AI Connection Error

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

(สงภาพหนาจอขอผิดพลาด) “แกบั”

**PROMPT (ENGLISH GLOSS)** *(A screenshot of the error was attached.) “Fix the bug.”* **OUTPUT RECEIVED** ChatGPT reported that the cause was that Ollama was not running, so port 11434 could not be reached. It started the service and checked that the backend was working normally, that the model qwen3.5:4b answered, and that the embedding model for retrieving data was available. The user was asked to send the question on the web page again and was told that Ollama must also be running whenever the AI assistant is used. No code change was needed this time. **VERIFIED AGAINST** The three checks reported by ChatGPT (backend, model response, and embedding model), as stated in the chat. **EDITS MADE** No code was changed in this exchange.

-- page 12 --

### Log 25: Preparing the Project for a Presentation Notebook

“บอกวิธีที่จะทําใหเพื่อนในโปรเจคเปิด project แลวเห็นทุกอยางเหมือนเราใหหนอย ตองการยายขอมูลไปเครื่องเพื่อน เพราะจะใช notebook ใน การนําไปเสนอ”

**PROMPT (ENGLISH GLOSS)** *“Please tell me how to make my teammate open the project and see everything the same as we do. I need to move the data to my* *friend's computer, because a notebook will be used for the presentation.”* **OUTPUT RECEIVED** ChatGPT recommended copying the whole project together with its database to the notebook and installing Python and Ollama there. It listed three things to prepare: the code and saved game data (the project folder including backend/data), the AI models (install Ollama and download the models), and browser data such as progress and chat history, which is not stored in the database and must be moved separately if needed. The steps were: (1) close the backend and ZIP the project folder, checking that games.sqlite3 (game data and content) is included, with embeddings.sqlite3 (search cache) optional; copying the folder is preferable to Git alone because the database may not be tracked in Git, and if BGT_DATABASE_PATH points elsewhere the database must be copied from there. (2) Extract the ZIP on the notebook, install Python and Ollama, run pip install -r backend/requirements.txt, and download the models qwen3.5:4b (answering questions), qwen3:1.7b (creating game drafts), and embeddinggemma (rule search) before presentation day. (3) Open Ollama, set the environment variables (BGT_ADMIN_PASSWORD, BGT_OLLAMA_URL, BGT_ASSISTANT_MODEL, BGT_OLLAMA_MODEL, and BGT_EMBED_MODEL), start the backend with python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000, and serve the Code folder with python -m http.server 5500. (4) Test before presenting: published games appear with lessons, rules, and quizzes; admin login works; at least one AI question is asked to load the model and check speed; the original PDF manuals are copied separately, since the database does not store PDFs; and OCR needs an Internet connection because the page downloads libraries and language data. **VERIFIED AGAINST** ChatGPT advised testing on the actual notebook before presenting. No test on another computer was shown in this exchange, and ChatGPT stated that AI speed depends on the notebook's specifications. **EDITS MADE** No code was changed in this exchange.

### Log 26: Creating a Backup ZIP Package

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ชวยจัดการเรื่อง backup zip โฟลเดอรใหหนอย”

**PROMPT (ENGLISH GLOSS)** *“Please take care of backing up the folder as a ZIP file.”* **OUTPUT RECEIVED** ChatGPT created a ZIP package ready to move to another computer, BoardGameTutor ZIP of 32.11 MB. It contains the code, the database with the 6 published games, the PDF manuals, and the startup scripts. The friend was told to extract the ZIP and read TRANSFER_GUIDE_TH.txt inside it to install Python, the dependencies, and the Ollama models before use, and that the chat history and progress saved in the browser on the original computer are not included. **VERIFIED AGAINST** ChatGPT reported checking the ZIP file and the database inside it. **EDITS MADE** ChatGPT created the ZIP package, which includes TRANSFER_GUIDE_TH.txt and the startup scripts. No existing source code was reported as changed.

-- page 13 --

### Log 27: Troubleshooting Missing Games on a Friend's Computer

(สงภาพหนาจอ) “เพื่อนรันแลวไมเจอเกมแกยังไง”

*(A screenshot was attached.) “My friend ran it and cannot find the games. How can this be fixed?”* **OUTPUT RECEIVED** ChatGPT checked the ZIP and reported that it contains all 6 games and that all of them are published; the screenshot alone did not show the cause. It gave the friend a checklist. First, open the game-data link from the backend: if it does not open, the backend is not running and must be started with python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 and left open, then press Ctrl+F5 on the page; if it shows [], the backend is using an empty or different database file; if it shows long game data, press Ctrl+F5 on the page, and if it is still empty send a screenshot of the link result together with the Console errors. Second, if it shows [], use the database from the ZIP: close the backend, extract the ZIP to a new folder to keep the friend's old data, check that backend\data\games.sqlite3 exists, open PowerShell in the new folder that contains README.md, set $env:BGT_DATABASE_PATH to that file, start the backend, open /api/games again to see 6 games, and press Ctrl+F5. ChatGPT added that listing the games does not need Ollama, so the backend and database should be checked first. **VERIFIED AGAINST** ChatGPT's inspection of the ZIP (6 games, all published), as reported in the chat. The checklist was not run on the friend's computer in this exchange. **EDITS MADE** No code was changed in this exchange.

### Log 28: Cloning from GitHub and Adding the Game Data

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“คือเพื่อน clone ใน Github ลงไปแลวตองทําไงตอ”

**PROMPT (ENGLISH GLOSS)** *“If my friend cloned the project from GitHub, what do they need to do next?”* **OUTPUT RECEIVED** ChatGPT explained that a plain clone from GitHub will not include the game data, because backend/data/ is set to be ignored by Git, so the database from the ZIP has to be added. The steps were: (1) extract the ZIP and copy the entire backend\data folder into the cloned project so that the file is at BoardGameTutor\backend\data\games.sqlite3, closing the backend first and backing up any existing data folder if the friend has already added data; (2) open PowerShell in the project folder that contains README.md and run python -m pip install -r backend/requirements.txt; (3) start the backend with BGT_ADMIN_PASSWORD and BGT_DATABASE_PATH set and the uvicorn command; (4) open another PowerShell and run python -m http.server 5500 --bind 127.0.0.1 --directory Code; (5) open the web page, press Ctrl+F5, and check that 6 games appear, also through the game-list API. If the AI is used, Ollama must be installed and the three models downloaded. ChatGPT added that each computer then stores its own data and that git pull will not bring the game data from the original computer. **VERIFIED AGAINST** ChatGPT's explanation of the Git ignore setting for backend/data/. The steps were not run on another computer in this exchange. **EDITS MADE** No code was changed in this exchange.

-- page 14 --

### Log 29: Connecting the Backend to Ollama

(สงภาพหนาจอขอความ 127.0.0.1:11434) “เชื่อมยังไง”

*(A screenshot of an error mentioning 127.0.0.1:11434 was attached.) “How do I connect it?”* **OUTPUT RECEIVED** ChatGPT explained that the message means the backend on the friend's computer cannot reach Ollama, and gave steps to do on the notebook that runs the project: (1) run ollama serve in PowerShell and leave the window open, noting that if the port is already in use then Ollama may already be running; (2) open the Ollama service link and look for “Ollama is running”, and if the ollama command is not found install Ollama first and open a new PowerShell; (3) in another PowerShell download the models qwen3.5:4b, qwen3:1.7b, and embeddinggemma if they are missing; (4) close the old backend with Ctrl+C and restart it from the project folder with BGT_OLLAMA_URL, BGT_ASSISTANT_MODEL, BGT_OLLAMA_MODEL, and BGT_EMBED_MODEL set and the uvicorn command. The user should then press Ctrl+F5 on the web page and ask again. ChatGPT added that 127.0.0.1 refers to the computer that is running, so Ollama must be open on that notebook as well. **VERIFIED AGAINST** The error text in the screenshot compared with the setup steps. The steps were not run in this exchange. **EDITS MADE** No code was changed in this exchange.

### Log 30: Data Stored for Each Board Game

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“บอรดเกมแตละอันมีขอมูลอะไรบาง”

**PROMPT (ENGLISH GLOSS)** *“What data does each board game have?”* **OUTPUT RECEIVED** ChatGPT reported that the database holds 6 games and that each stores: general information (name, description, number of players, playing time, category, difficulty, and publish status); lessons (setup and step-by-step play); rules (rules and abilities of the cards or roles); practice scenarios and quizzes (question, options, correct answer, and explanation); and data for the AI assistant (manual text, sources, game edition, and question-and-answer pairs checked against the rules). It gave counts per game of lessons, rule topics, practice scenarios, quizzes, and verified answers: Exploding Kittens 6/5/3/3/5, Werewolf 6/6/2/3/3, Mogel Motte 7/5/3/3/4, Forbidden Words 5/3/2/2/3, Spyfall 7/5/2/3/3, and For Sale 2/3/3/3/3. It also summarized the content covered for each game. ChatGPT pointed out two items to fix before presenting: Werewolf has no manual text or reference edition yet, and for For Sale the player-count field is recorded as “ผูเลน 2 ชวง” and the playing time as “ไมระบุ” (not specified). **VERIFIED AGAINST** ChatGPT's reading of the project database, as reported in the chat. The counts were not separately recounted in this record. **EDITS MADE** No code or data was changed in this exchange. The two data issues were listed as items to check before the presentation.

-- page 15 --

### Log 31: Where the AI Assistant Data Is Stored

“ขอดูหนอย ขอมูลผูชวย AI เก็บไวตรงไหน ขอตัวอยางขอมูลหนอย”

*“Show me where the AI assistant data is stored, with an example of the data.”* **OUTPUT RECEIVED** ChatGPT explained that the AI assistant data is stored in games.sqlite3, in the games table, where the payload column holds each game as JSON including its AI data. It showed a real Exploding Kittens record with the fields id, n, edition (“Exploding Kittens — Original Edition, English”), source_type (“manual”), source_url (the publisher's rules page), and source_text, which is the manual text extracted from a PDF, about 9,500 characters for this game (shortened in the example). It also showed the Thai rules in the field r, for example the Nope card, and the verified answers in the field verified_qa, with a sample about whether Nope can cancel Defuse. Each verified answer has the fields question, aliases (differently worded questions with the same meaning), answer, source_id (for example R1 for the first rule), quote (the rule text that supports the answer), and reviewed (marks that the answer was checked). The data can be viewed on the admin page under the guide for the AI assistant and verified answers, or through the game-list API. The file embeddings.sqlite3 only stores the vector cache for text search. **VERIFIED AGAINST** A record read from the project database by ChatGPT, as shown in the chat. **EDITS MADE** No code or data was changed in this exchange.

### Log 32: How the AI Uses the Stored Data

**TOOL USED ChatGPT** **PROMPT (AS USED, THAI)**

“ขอมูลพวกนี้ AI จะเอาไปทําอะไรตอ”

**PROMPT (ENGLISH GLOSS)** *“What does the AI do with this data?”* **OUTPUT RECEIVED** ChatGPT explained that the data is used as reference sources for the rule assistant and is not used to retrain the model; the data is retrieved at answer time and given to the model to read. Using the question “Can Nope cancel Defuse?” as an example, the system (1) selects only the data of the game being asked about; (2) checks the admin-verified answers (verified_qa) and, if the question matches, answers immediately from that data; (3) otherwise searches the rules and manual text (lessons, rules, and source_text) by keywords and by meaning, with embeddings helping to find the text; (4) sends the question with the evidence to the model through Ollama, which arranges it as a Thai answer and uses the recent conversation to understand follow-up questions; and (5) checks the answer against the evidence before showing it, and if it cannot be confirmed it states the limitation and shows the rules that were found instead. The edition and source_url fields tell which manual an answer refers to and where it came from. ChatGPT cautioned that the completeness and correctness of the stored data directly affect answer quality, and that checking with the model can still be wrong. **VERIFIED AGAINST** ChatGPT's description of how the assistant works, as stated in the chat. It was not compared with the code in this record. **EDITS MADE** No code or data was changed in this exchange.

-- page 16 --

## Part 2 — Claude (Board Game Tutor Prototype)

### Log 01: Requirements Analysis and Initial Prototype

**TOOL USED Claude**

“ผมจะทําเว็บเป็นตัวโปรโตไทป นี้คือเอกสาร SRS ผมอยากใชภาษา HTML CSS และ JavaScript เทานั้นในการเขียน ผมมีตัวอยางหนาเว็บที่ ออกแบบแลวใหคุณดู คุณชวยออกแบบเพิ่มเติมตามเท็มเพลตที่ผมใหไปใหเสร็จสมบูรณ”

**PROMPT (ENGLISH GLOSS)** *“I am building the website as a prototype. This is the SRS document. I want to write it using only HTML, CSS, and JavaScript. I have an* *example of a page design for you to look at. Please complete the design by extending it according to the template I provided.”* **OUTPUT RECEIVED** A single-file HTML/CSS/JavaScript prototype of the Board Game Tutor covering the seven functional requirements in the SRS (FR-1 to FR-7): game search, step-by-step lessons, scenario practice, quizzes, keyword rule search, learning progress, and an admin page. Two sample games (Ticket to Ride and Carcassonne) were used as placeholder content. **VERIFIED AGAINST** The SRS document and the list of functional requirements. The design template had not actually been attached at this point, so the visual style was chosen by the AI rather than copied from the template. The JavaScript was not opened in a real browser. **EDITS MADE** The prototype was kept as a draft so that it could be restyled once the template was provided. The sample game content was treated as unverified and was to be checked against the official rules before real use. It was also noted that progress stored in the browser's localStorage and the simulated admin login are prototype-only and not real user accounts.

### Log 02: Redesign Following the Provided Template

**TOOL USED Claude** **PROMPT (AS USED, THAI)**

“นี่คือตัวอยางเทมเพลต สรางใหผมใหม”

**PROMPT (ENGLISH GLOSS)** *“This is the example template. Please create it again for me.”* **OUTPUT RECEIVED** A redesigned prototype that follows the template: a collapsible left sidebar with a logout button, a capsule-shaped search bar at the top, a “popular games” card, and four colored category tiles that filter the games. Additional pages were designed in the same style: user profile, history, suggestions, learning progress, and admin management. **VERIFIED AGAINST** The layout of the template image and the SRS requirements. The JavaScript was checked for syntax errors, but it had not yet been opened in a real browser. **EDITS MADE** Carcassonne was chosen as the popular game because its number of players and playing time matched the template. The Party category was left empty with a placeholder message until the admin adds a game to it. The logout button only exits admin mode because the prototype has no real user accounts.

-- page 17 --

### Log 03: Source Code Export for GitHub

**TOOL USED Claude**

“ผมตองการโคดทัง้หมดเพื่อเอาไป commit ใน GitHub”

*“I need all of the code so that I can commit it to GitHub.”* **OUTPUT RECEIVED** The code split into four files (index.html, style.css, script.js, and README.md), together with the git commands for committing and pushing, and instructions for hosting the page with GitHub Pages. The README described the project, how to run it, and a table of features mapped to the SRS. **VERIFIED AGAINST** The files were checked for JavaScript syntax errors, and the file structure was compared with the original single-file version. They were not opened in a real browser after being split. The Thai font is loaded from Google Fonts, so an Internet connection is needed on first use. The SRS lists the GitHub repository as NONE, so the repository link still has to be added after creating it. **EDITS MADE** The files were downloaded into one folder, and index.html was opened by double-clicking before committing. The README was written in Thai and can be edited to fit the project.

### Log 04: Single-File Version for VS Code

**TOOL USED Claude** **PROMPT (AS USED, THAI)**

“ผมอยากไดโคดทัง้หมดที่กอปใสใน VS Code ในโฟลเดอรที่มีนามสกุล .html แลวใชไดเลย ทําไดมัย้ถาทําไมไดบอกวิธีอื่นเพิ่มเติมดวย”

**PROMPT (ENGLISH GLOSS)** *“I want all of the code in a form that I can copy into VS Code, save in a folder with an .html extension, and use immediately. Is that* *possible? If not, please tell me other methods as well.”* **OUTPUT RECEIVED** Confirmation that the HTML, CSS, and JavaScript are contained in a single index.html file of about 24 KB, with steps for copying it into VS Code, saving it, and opening it with Live Server or by double-clicking. Alternative methods were also given: downloading the file directly, using the four-file folder for GitHub, and viewing the published page link. **VERIFIED AGAINST** The file size and contents of the single-file version, and the copy-and-save steps. An Internet connection is needed on first load for the Thai font; without it the page still works with a system font. **EDITS MADE** No changes were made to the code. The single-file version was used for local testing, and the four-file folder was kept for committing to GitHub.

-- page 18 --

### Log 05: Replacing the Sample Games

**TOOL USED Claude**

“ผมอยากใหเอาโคดเดิม มาเขียน และเปลี่ยนทัง้หมดเกมตอไปนี้เขาไปใหผมหนอย 1.Exploding Kittens 2.Werewolf 3.Mogel Motte 4.คําตอง หาม และ 5.Spyfall ชวยเพิ่มเกมเหลานี้ลงไปในเว็บของผมหนอย”

**PROMPT (ENGLISH GLOSS)** *“Please take the existing code and replace all of the games with the following: 1. Exploding Kittens, 2. Werewolf, 3. Mogel Motte, 4.* *Forbidden Words, and 5. Spyfall. Please add these games to my website.”* **OUTPUT RECEIVED** The code updated with five new games, each with its own lessons, practice scenarios, quiz questions, and searchable rules. The four categories were filled, and the updated files were provided both as a single index.html and as a four-file folder. **VERIFIED AGAINST** The updated code was checked for JavaScript syntax errors. The rules of Mogel Motte and Spyfall were compared with rules found online, while Exploding Kittens and Werewolf were written from standard published rules. For Forbidden Words, only the core mechanics were confirmed: each player has a forbidden word on their forehead, may not say their own word, and must get other players to say it. The player counts (“3+”) and playing time (“15-30”) were not confirmed, and the penalties and scoring were not confirmed. **EDITS MADE** The storage key used in the browser was renamed so the new games appear immediately; previously saved learning progress is reset. The Werewolf lessons were kept to the basic roles (villager, werewolf, seer), and the unconfirmed details of Forbidden Words were to be checked against the rules in the game box and corrected if needed.

### Log 06: Adding Illustrations to Rule Explanations

**TOOL USED Claude** **PROMPT (AS USED, THAI)**

“ผมอยากใหการอธิบายกฎเกมมีภาพประกอบดวยชวยใหเขาใจงายขึน้ ยกตัวอยาง เชน Werewolf เวลาอธิบาย role ใหมีการดขึน้มาใหดู ประกอบดวย”

**PROMPT (ENGLISH GLOSS)** *“I want the game rule explanations to include illustrations that make them easier to understand. For example, when Werewolf explains* *the roles, a card should appear for the user to look at.”* **OUTPUT RECEIVED** Card graphics added to the lessons, the game rule sections, and the rule search results. They are drawn in the code with emoji, colors, and text, so no image files are needed. Examples include the four role cards in Werewolf, the Attack, Skip, Favor, Shuffle, See the Future, Nope, and Defuse cards in Exploding Kittens, the numbered 1-5 cards in Mogel Motte, the location cards in Spyfall, and the hidden word card in Forbidden Words. **VERIFIED AGAINST** The pages were tested in a simulated browser with no errors reported. The layout has not been viewed on a real screen, so the card size and appearance still need to be checked by eye. **EDITS MADE** The browser storage key was renamed again, so the saved progress resets when the new version is first opened. The emoji cards can be replaced with real images or icons if the image files are provided.

-- page 19 --

## Part 3 — Copilot (Git Workflow)

### Log 01: Creating and Pushing a Git Branch

**TOOL USED Copilot**

“ขอวิธีสร้าง branch ชื่อ AI_logs และส่ง branch ขึ้น GitHub”

**PROMPT (ENGLISH GLOSS)** *“How do I create a branch named AI_logs and push it to GitHub?”* **OUTPUT RECEIVED** In the VS Code terminal, run `git checkout -b AI_logs` to create the branch and switch to it. Then run `git push -u origin AI_logs` to publish the branch to GitHub. The current branch name can be checked in the lower-left corner of VS Code. **VERIFIED AGAINST** These commands are valid when the terminal is in a Git repository with a GitHub remote named `origin`. **EDITS MADE** No code or branch was changed; the instructions were added to this record for later use.
