# J26-IT-304: AI-Based Adaptive Programming Learning Platform with Automated Code Evaluation and Teacher Analytics

## 📖 Project Overview
Java programming is a foundational but high-failure-rate subject for orientation and first-year undergraduate students. This project (J26-IT-304) replaces traditional static, one-size-fits-all instructional approaches with a fully personalized, data-driven adaptive learning environment. The platform integrates four core AI modules—a Curriculum-Aware RAG Chatbot, an Adaptive AI Voice Tutor, a Mastery-Based Quiz Generator, and an Attention-Monitored Video Learning System—all synchronized through a shared student profile layer.

## 🚨 Problem Statement
* **Premature Exposure:** Standard AI chatbots provide unrestricted responses, exposing beginners to advanced concepts before they have learned the prerequisites.
* **Fake Confusion Detection:** Existing voice tutors rely on fixed keyword rules rather than trained ML classifiers, failing to distinguish between genuine learning difficulty and simple student preference.
* **Compounding Knowledge Gaps:** Static assessments allow students to progress without genuinely mastering individual concepts, leaving compounding knowledge gaps.
* **Passive Video Consumption:** Video-based learning lacks real-time attention monitoring, meaning missed topics are never mapped to personalized post-video assessments.

## 🎯 Project Objectives
1. **Curriculum Gating:** Restrict AI chatbot retrieval to only the concepts a student has successfully completed in their lectures.
2. **Dynamic Strategy Escalation:** Detect confusion from spoken/text natural language and escalate pedagogical strategies (Theory $\rightarrow$ Example $\rightarrow$ Simplified $\rightarrow$ Analogy) dynamically.
3. **Mastery-Based Progression:** Continuously generate targeted questions based on a Java Knowledge Graph until a student achieves a strict mastery threshold.
4. **Attention-to-Assessment Loop:** Map real-time webcam attention to transcript-defined topics, using distraction tiers to sequence the difficulty of generated MCQs.

---

## ✅ Core System Components & PP1/PP2 Progress Checklist

This section outlines the individual contributions, completed Progress Presentation 1 (PP1) milestones, and the roadmap for Progress Presentation 2 (PP2).

### Component 1: Curriculum-Aware RAG-Based AI Chatbot
**Owner:** Mapatuna M.D.N (IT23157682)
*Retrieval restricted to the lectures a student has completed, inside a live coding environment.*

**PP1 Contributions (Completed) 🏆**
- [x] Implemented Curriculum Gate: Retrieval strictly limited to completed lectures.
- [x] Set up local embeddings, Vector DB, and LLM in a single RAG pipeline.
- [x] Designed the UI with Problem description, test cases, and code editor.
- [x] Added content-margin validation to avoid blocking valid questions that overlap with locked lecture topics.

**PP2 Roadmap (In Progress) 🚀**
- [ ] Add all remaining lectures and course materials to the Vector Database.
- [ ] Finalize seamless integration of the chatbot panel with the live coding workspace.
- [ ] Fine-tune the LLM prompt templates for more accurate and pedagogically sound replies.

### Component 2: Adaptive AI Voice Tutor for Java Programming
**Owner:** Lakmal H.U.A.D.Y (IT23335578)
*ML-driven confusion detection and multi-tier strategy escalation.*

**PP1 Contributions (Completed) 🏆**
- [x] Trained and integrated Hybrid Confusion Classifier (TF-IDF + Logistic Regression) with rule-based safety guards.
- [x] Built the Multi-Tier Adaptive Strategy Engine (Theory, Example, Simplified, Analogy).
- [x] Decoupled Local LLM Pipeline (Ollama) with dynamic response generation and deterministic template fallbacks.
- [x] Implemented seamless toggle between voice input and text chat in the UI.
- [x] Replaced generic confirmation prompts with concept-checking questions to detect real understanding.

**PP2 Roadmap (In Progress) 🚀**
- [ ] Expand offline STT (Speech-to-Text) and TTS (Text-to-Speech) benchmarks for full hands-free mode.
- [ ] Implement personalized strategy prioritization using the student's historical learning data.
- [ ] Aggregate multi-session weakness logs and display them on the student dashboard.

### Component 3: Mastery-Based Adaptive Java Quiz Generation
**Owner:** Rathnayake R.M.G.M (IT23182714)
*Identifies weak Java concepts and dynamically generates new practice questions until mastery.*

**PP1 Contributions (Completed) 🏆**
- [x] Built the Learner Dashboard showing overall progress and a module dropdown for 10 specific modules.
- [x] Developed the adaptive quiz interface displaying learning sets, questions, and immediate explanatory feedback.
- [x] Implemented remedial practice logic to pull new questions based on identified weak concepts.
- [x] Created the mastery progression gate (learners advance only when meeting the required score threshold).

**PP2 Roadmap (In Progress) 🚀**
- [ ] Rigorously test adaptive LLM question generation against the Java Knowledge Graph.
- [ ] Refine weak-topic remediation algorithms based on early user interaction data.
- [ ] Evaluate system accuracy (non-repetitive question generation) and overall usability.

### Component 4: Attention-Monitored Video Learning System
**Owner:** Haputhanthrie D.D (IT23166110)
*Maps low-attention timestamps to specific video topics to drive post-video MCQ generation.*

**PP1 Contributions (Completed) 🏆**
- [x] Trained YOLOv8n Attention model (0.81 mAP50) on classroom images for student states.
- [x] Integrated MediaPipe for face checking (video pauses if no face is detected).
- [x] Built the Question Engine to generate 10 MCQs from the transcript, mapped to distraction times.
- [x] Implemented weighted marking (Easy=1, Medium=2, Hard=3) based on attention metrics.
- [x] Ensured privacy-by-design (No cloud services, no stored video, local camera processing only).

**PP2 Roadmap (In Progress) 🚀**
- [ ] Implement the Pass/Fail check (50% threshold) to unlock the next video module.
- [ ] Send identified weak topics and marks to the shared Knowledge Graph/Learner Profile.
- [ ] Add English subtitles directly from the timestamped transcript for accessibility.
- [ ] Finalize the post-quiz result screen to explicitly list the timestamps where the student lost focus.

---

## 🏗️ System Architecture
The platform utilizes a **microservices-inspired architecture** operating on a strictly **Local-First** basis to ensure data privacy and zero API costs.
1. **Shared Learner Profile:** A centralized database tracks per-concept mastery, attention scores, and strategy effectiveness.
2. **Frontend Layer:** React.js interfaces integrating the IDE, video player, voice chat, and quiz dashboard.
3. **Backend Intelligence Layer:** FastAPI microservices handling RAG retrieval, ML Classification, Attention Analysis, and Mastery Gating.
4. **Local LLM Layer:** Ollama running quantized models (`llama3.2:3b`, `Qwen2.5-Coder`) to generate responses and MCQs natively on institutional hardware.

## 📊 Data Collection & Ethical Approval
*   **Data Minimization:** No raw webcam frames, voice audio, or identifiable biometric data are ever saved to the disk or transmitted externally. All processing (MediaPipe, YOLO, Faster-Whisper) occurs in-memory.
*   **Datasets:** Used public datasets (DAISEE for engagement mapping, synthetic HuggingFace datasets for confusion detection training). 
*   **Consent:** Explicit UI indicators and opt-in toggles are required before the camera or microphone activates. Human participant evaluation in PP2 is subject to SLIIT ethical review board approval.

## 🧠 Machine Learning Pipeline
*   **Voice Tutor:** `Text -> TF-IDF Vectorizer -> Logistic Regression -> Strategy Class`
*   **Video Attention:** `Webcam Frame -> MediaPipe (Landmarks) + YOLOv8n (Engagement) -> Time-Series Aggregation -> Attention Tier`
*   **Generative Pipelines:** `Context (Transcript/Completed Lectures) -> Prompt Template -> Local LLM -> Output Parser -> Filter/Validation`

## 💻 Technology Stack
*   **Frontend:** React 19, TypeScript, Vite, Tailwind CSS
*   **Backend:** Python 3.13, FastAPI
*   **Local AI / LLMs:** Ollama, Llama 3.2, Qwen2.5-Coder
*   **Computer Vision & Audio:** OpenCV, MediaPipe, YOLOv8n, Faster-Whisper, Piper TTS
*   **Data Science:** Scikit-Learn, Pandas, NumPy
*   **Vector Database:** ChromaDB / FAISS (for RAG)

## 📁 Project Structure Overview (Monorepo)
```text
J26-IT-304/
├── backend/                  # FastAPI Backend Service (Adaptive AI Voice Tutor)
│   ├── app/                  # Application source code
│   │   ├── classifier/       # Hybrid confusion classifier (TF-IDF + Logistic Regression & rules)
│   │   ├── escalation/       # Multi-tier pedagogical strategy escalation engine & session tracking
│   │   ├── generation/       # LLM prompt builder, Ollama adapter & deterministic template fallbacks
│   │   ├── config.py         # Application configuration & environment settings
│   │   ├── orchestrator.py   # Pipeline orchestration between classifier, engine, and LLM
│   │   ├── schemas.py        # Pydantic data models and API request/response schemas
│   │   └── topics.py         # Java topic catalogue and curriculum scope definitions
│   ├── benchmarks/           # Performance, latency, and response quality benchmarks
│   ├── models/               # Trained model artifacts (clf-v1.0.0 confusion classifier)
│   ├── scripts/              # Utility scripts for data validation and model testing
│   ├── tests/                # Pytest unit and integration test suites
│   ├── compose.yaml          # Docker Compose container orchestration
│   ├── Dockerfile            # Container build specification
│   └── requirements.txt      # Python runtime dependencies (Python 3.13)
├── frontend/                 # React 19 + TypeScript + Vite + Tailwind CSS Web Application
│   ├── src/
│   │   ├── components/       # Reusable UI & shader/canvas visualizer components
│   │   ├── features/
│   │   │   └── tutor/        # Voice tutor UI, audio visualizers (Aura & Wave), chat & episode store
│   │   ├── hooks/            # Custom React hooks (speech input, microphone, media streams)
│   │   ├── lib/              # Shared helper functions and utility definitions
│   │   ├── index.css         # Styling system, design tokens, and theme configurations
│   │   └── main.tsx          # Application entry point
│   ├── public/               # Static assets, branding, and icons
│   ├── package.json          # Node dependencies & project build scripts
│   └── vite.config.ts        # Vite build tool and development server configuration
├── experiment1/              # Research & ML Experiments for Confusion Classifier
│   ├── confusion_baseline/   # Baseline model architectures and benchmark comparisons
│   ├── data/                 # Training, validation, and probe datasets
│   ├── models/               # Serialized classifier weights, vectorizers, and metrics
│   ├── notebooks/            # Jupyter notebooks for data analysis and model training
│   ├── probe/                # Behavioral probe test cases and diagnostic suites
│   ├── reports/              # Experiment logs and evaluation results
│   └── scripts/              # Data generation, cleaning, and preprocessing pipelines
├── SETUP.md                  # Comprehensive developer setup guide (backend, frontend, Ollama)
└── README.md                 # System architecture, research documentation, and progress checklist
```

## 🖥️ Demo UI Prototype for Used Data Collection
The platform's UI serves as the primary data collection point for the ML models in a non-intrusive way:
1.  **Voice / Text Toggle:** Students switch to voice mode, passing microphone blobs to the backend for STT, yielding text data for the TF-IDF classifier.
2.  **Webcam Panel (Video Learning):** A small, indicator-lit preview window shows the student they are being monitored. In-memory frames are processed to yield bounding boxes and EAR (Eye Aspect Ratio) scores.
3.  **Quiz Selections:** Radio buttons and submit actions feed directly into the mastery progression algorithm, silently updating the shared database's knowledge graph nodes.
4.  **IDE Workspace:** Keystrokes and run-button clicks inside the React code editor are logged to correlate active coding time against chatbot queries.
