# AGENTS.md

## Project

This repository contains the final-year research project:

**AI-Based Adaptive Java Learning Platform**

The platform consists of four integrated AI-based learning components designed for beginner/first-year Java programming learners.

### Components

* **Component 1:** Curriculum-aware RAG AI Chatbot
* **Component 2:** Adaptive AI Voice Tutor for Java Programming
* **Component 3:** Mastery-Based Adaptive Java Quiz
* **Component 4:** Attention-Monitored Adaptive Video Learning

The project is a university research project. Code, experiments, datasets, evaluation procedures, and results must be treated as research artifacts.

---

# 1. General AI Coding Rules

Before making changes:

1. Inspect the existing repository.
2. Understand the relevant component and shared architecture.
3. Do not unnecessarily modify unrelated components.
4. Do not rename existing folders or files without explicit permission.
5. Do not delete files without explicit permission.
6. Do not introduce major architectural changes without explaining them first.
7. Prefer small, testable changes.
8. Keep existing functionality working.
9. Do not create fake implementations that appear to be completed research functionality.
10. Do not fabricate experimental results, accuracy values, F1 scores, learning gains, or evaluation results.
11. Do not fabricate datasets or research evidence.
12. Never commit API keys, passwords, tokens, or other secrets.
13. Use environment variables for secrets.
14. Update documentation when an architectural decision changes.
15. Add or update tests when implementing functionality.

---

# 2. Architecture

The repository uses a single integrated backend and frontend architecture.

Shared functionality belongs under:

```text
backend/shared/
```

Shared functionality includes:

* authentication
* learner profile
* database access
* integration contracts
* cross-component events

Do not duplicate shared learner-profile logic inside individual components.

Components should communicate through defined interfaces/contracts rather than directly modifying another component's internal implementation.

---

# 3. Component Boundaries

## Component 1

Location:

```text
backend/component1_rag/
```

Purpose:

Curriculum-aware retrieval-augmented generation for Java learning.

Do not modify Component 1 while working on another component unless integration work requires it.

---

## Component 2

Location:

```text
backend/component2_voice_tutor/
```

Purpose:

Adaptive AI voice tutor for beginner Java programming learners.

Main research pipeline:

```text
User Voice/Text
      â†“
Speech-to-Text
      â†“
Confusion Detection
      â†“
Strategy Selection
      â†“
Response Generation
      â†“
Text-to-Speech
      â†“
Interaction Logging
      â†“
Learner Profile / Weakness History
```

The core adaptive teaching strategies are:

```text
Theory
   â†“
Example
   â†“
Simplified Explanation
   â†“
Analogy
```

The system should also support learner-requested strategy overrides.

Example:

```text
"Give me an example"
```

should be interpreted as a request for an example-based explanation rather than blindly following the automatic strategy.

Repeated confusion should trigger escalation through the teaching strategies.

---

# 4. Component 2 Research Rules

The confusion classifier is intended to use:

```text
TF-IDF
+
Logistic Regression
```

A simple rule/keyword-based detector may be used temporarily during early prototyping, but it must not be represented as the final research model.

The classifier should eventually provide measurable outputs that can be evaluated using appropriate classification metrics.

Do not claim target metrics have been achieved until experiments have actually been executed.

---

# 5. Component 2 Personalization

The tutor should maintain learner interaction information such as:

* topic
* learner question
* confusion status
* selected strategy
* strategy override
* attempt number
* resolution status
* strategy effectiveness
* weakness history

Weakness information should be stored through the shared learner-profile architecture where appropriate.

Do not create a completely separate learner-profile database inside Component 2.

---

# 6. Component 2 Module Responsibilities

## speech/

Responsible for:

* audio preprocessing
* speech-to-text
* text-to-speech

The intended stack may include local speech-processing technologies such as Faster Whisper and Piper, but dependencies should only be finalized when implementation begins.

---

## confusion/

Responsible for:

* text preprocessing
* feature extraction
* confusion classification
* confusion detection

Expected research approach:

```text
Text
 â†“
Preprocessing
 â†“
TF-IDF
 â†“
Logistic Regression
 â†“
Confusion Prediction
```

---

## strategy/

Responsible for:

* strategy definitions
* automatic strategy selection
* escalation
* learner-requested strategy overrides

---

## response/

Responsible for:

* constructing response context
* building prompts where required
* generating tutor responses

Do not put confusion classification logic inside the response generator.

---

## personalization/

Responsible for:

* weakness logging
* strategy history
* personalized strategy priorities

---

## session/

Responsible for:

* current learning-session state
* interaction management
* tracking the current explanation cycle

---

## evaluation/

Responsible for research evaluation code.

Do not place production logic inside evaluation modules.

---

# 7. Shared Learner Profile

The learner profile is a shared platform-level concept.

Potential information includes:

```text
user_id
weak_topics
topic_history
confusion_history
strategy_history
mastery_information
interaction_history
```

The exact schema must be agreed through:

```text
backend/shared/contracts/
```

Do not silently create incompatible schemas in individual components.

---

# 8. Data Rules

Use the following separation:

```text
data/raw/
data/processed/
data/external/
```

Never modify raw research data unnecessarily.

Processed datasets must be reproducible from documented preprocessing steps whenever practical.

Do not commit sensitive personal learner data.

Do not commit secrets.

Do not commit unnecessarily large generated files.

---

# 9. Machine Learning Rules

ML models must have:

* documented training data
* documented preprocessing
* reproducible training procedures
* saved model artifacts where appropriate
* evaluation metrics
* experiment records

Do not report model performance without actually running the evaluation.

For example, never write:

```text
F1 = 0.87
```

unless that value was produced by an actual experiment.

---

# 10. Research Integrity

This is a university research project.

AI coding agents must not:

* fabricate results
* fabricate citations
* fabricate datasets
* fabricate user studies
* fabricate participant responses
* fabricate accuracy metrics
* fabricate learning gains
* claim an experiment was performed when it was not

If information is missing, clearly state that it needs to be provided or researched.

---

# 11. API Rules

API routes belong inside the relevant component:

```text
backend/component1_rag/api/
backend/component2_voice_tutor/api/
backend/component3_quiz/api/
backend/component4_video/api/
```

Shared APIs belong under:

```text
backend/shared/
```

Keep request/response formats consistent with:

```text
backend/shared/contracts/
```

Do not change an API contract without considering the effect on other components.

---

# 12. Testing

Tests should be added progressively.

Important testing levels:

```text
tests/unit/
tests/integration/
tests/evaluation/
```

Component 2 should eventually include tests for:

* confusion preprocessing
* confusion classification
* confusion detection
* strategy selection
* strategy override
* escalation
* weakness logging
* session state
* API behavior

Research evaluation tests should remain separate from normal unit tests.

---

# 13. Privacy

The system handles learner-related information.

Avoid unnecessary collection or storage of personal information.

For Component 4, webcam processing should follow the project's privacy design.

Raw webcam frames should not be stored or shared unless explicitly required and approved by the project design/ethics requirements.

---

# 14. Dependencies

Do not install a large number of dependencies without justification.

Before adding a dependency:

1. Check whether an existing dependency already provides the required functionality.
2. Consider project compatibility.
3. Consider whether it is necessary for the research objective.
4. Add it to the appropriate dependency file.
5. Document important dependency decisions where appropriate.

---

# 15. Code Style

Prefer:

* clear names
* small functions
* modular architecture
* type hints where practical
* meaningful docstrings for important modules/functions
* explicit error handling
* testable code

Avoid:

* giant files
* giant functions
* duplicated logic
* hard-coded secrets
* unnecessary global state
* hidden side effects
* unnecessary abstraction

---

# 16. AI Agent Workflow

When asked to implement a feature:

### Step 1

Inspect the relevant files.

### Step 2

Explain briefly what needs to change.

### Step 3

Implement the smallest complete change.

### Step 4

Run relevant tests or validation.

### Step 5

Fix errors.

### Step 6

Report:

* files changed
* what was implemented
* tests performed
* remaining limitations

Do not modify unrelated files merely to make the repository appear more complete.

---

# 17. Component 2 Implementation Order

When implementing Component 2, prefer this progression:

```text
1. Project configuration
        â†“
2. Confusion preprocessing
        â†“
3. TF-IDF feature extraction
        â†“
4. Confusion classifier
        â†“
5. Confusion detector
        â†“
6. Strategy definitions
        â†“
7. Strategy selector
        â†“
8. Strategy override
        â†“
9. Escalation engine
        â†“
10. Response generation
        â†“
11. Weakness logging
        â†“
12. Strategy history
        â†“
13. Session management
        â†“
14. Speech-to-text
        â†“
15. Text-to-speech
        â†“
16. API integration
        â†“
17. Evaluation
        â†“
18. Integration with shared learner profile
```

Do not skip directly to the final voice system before the core adaptive logic is tested.

---

# 18. Integration

The four components must eventually work as one platform.

Important shared concepts include:

```text
User
Learner Profile
Topic
Weakness
Mastery
Interaction
Event
```

Component 2 should produce useful learner information that can eventually be consumed by Components 3 and 4.

For example:

```text
Component 2
     â†“
Weak Java Topic
     â†“
Shared Learner Profile
     â†“
Component 3 Quiz
```

and:

```text
Component 2
     â†“
Weakness / Learning History
     â†“
Shared Learner Profile
     â†“
Component 4 Video Learning
```

Do not create direct, tightly coupled dependencies between component internals.

---

# 19. Documentation

Important architecture decisions should be documented under:

```text
docs/architecture/
docs/decisions/
```

Research-related documentation belongs under:

```text
docs/research/
research/
```

Keep documentation synchronized with major architectural changes.

---

# 20. Current Development Principle

The repository will be developed incrementally.

At any point, prioritize:

```text
Correctness
>
Research validity
>
Testability
>
Integration compatibility
>
Maintainability
>
Feature completeness
```

Do not rush to implement every folder simply because the folders exist.

Empty modules are acceptable during early development.

---

# 21. Final Rule

When uncertain about an architectural decision:

**Do not silently make a major decision.**

Instead:

1. Identify the ambiguity.
2. Explain the relevant options.
3. Recommend the option based on the existing project architecture and research requirements.
4. Ask for confirmation if the decision could affect other components.

The goal is to build a reliable, reproducible, research-oriented AI learning platform rather than simply generating large amounts of code.
