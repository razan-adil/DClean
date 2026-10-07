# Group 2 Approach and solution

We first were assigned a problem of handling messy data with a model. But what kind and how to approach this problem the proper way?

---

# How can we apply AI?

When we studied the problem we found out that AI can not be a magical solution that sovles this problem; and we have reasons.
AI is Stochastic, data are Deterministic. AI provide a probability of success (Confidenece, Accuracy, etc..) if we integerated AI to the data the problem will still be the same, but the cleaning would scale from bad input to AI Halucinations. So we had impelement AI Reasonably.

---

# Generic Pipline

To automate the cleaning proccess we had to make a general pipline that takes any structred data files (CSV, Excel) and then output the same format with cleaned data.

that how we started making answers to questions:
- What is clean data?
- How to generalize?
- Where to apply the AI?

---

# Data groups#:

1. Identity: This data is the data where it has the identification info about the user: Name, Email, Phone (+966).
2. Structed/MetaData: This data is a data where it doesnt identficate the person but tells additional info about him: Major, University.
3. Catagorical/MultiSelcet: This data is usually a multi select data such as: Skills, agreement.
4. Free-Form: This data is the free form space where it takes from the user an input of a question like: Why do you want to join.

---

# The pipeline:

1. Contractor: Maps stochastic column headers to deterministic internal fields using a specialized Transformer NLP Classifier (DistilBERT / ONNX).
2. Normalization: Cleans and handles values using deterministic domain rules for each data type.
3. DeDuplication: Resolving duplicates across submissions using unsupervised entity resolution (MDM / Splink).
4. Storage & Export: Loads cleaned data into an auditable SQLite database and formatted Excel output.

---

# Why a Transformer NLP Classifier over a Generative LLM?

- **Zero Hallucination**: Constrained sequence classification (Softmax strictly over the 4 defined schema groups). A generative LLM can hallucinate non-existent categories; a sequence classifier is mathematically bound to valid groups.
- **5ms CPU Inference**: Distilled encoder model running on pure CPU via ONNX Runtime (~30MB footprint) vs. 2,000–5,000ms latency on generative LLMs.
- **Calibrated Confidence**: Direct softmax probabilities ($P \in [0, 1]$) provide genuine mathematical confidence scores to drive quarantine and routing thresholds.
- **Privacy & Cost**: 100% local in-house execution with zero API fees and zero data leakage to cloud endpoints.

