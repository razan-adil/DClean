"""
Transformer NLP Model Training & Synthetic Dataset Generation Pipeline.

This script implements an end-to-end AI workflow to:
1. Harvest real tabular column headers and actual respondent values directly from
   raw spreadsheets in RawData/ (e.g. Developers_Committee_2026_Responses.xlsx,
   Distraction_Era_Workshop_Dataset.xlsx, MultiSheet_Workshop_Batches.xlsx).
2. Extract verified ground-truth labels from config/ contracts.
3. Apply realistic data augmentations (subsampling, noise prefixes, casing, and permutations).
4. Train and export:
   a) Ultra-fast Calibrated Scikit-Learn TF-IDF Sequence Classifier (<1ms inference) -> models/tfidf_column_classifier.joblib
   b) Fine-tuned PyTorch / Hugging Face Transformer Classifier -> models/transformer_column_classifier/
"""

import os
import sys
import json
import random
import argparse
import openpyxl
import yaml
from typing import List, Dict, Any, Tuple, Optional

# Ensure workspace root is on sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# The 4 canonical guideline schema groups
LABEL_MAP = {
    "Identity": 0,
    "Structured/MetaData": 1,
    "Categorical/MultiSelect": 2,
    "Free-Form": 3
}
ID2LABEL = {v: k for k, v in LABEL_MAP.items()}

# =====================================================================
# 1. Synthetic Template Pool (for balanced augmentation)
# =====================================================================

SYNTHETIC_TEMPLATES = {
    "Identity": {
        "headers": [
            "الاسم الكامل", "الاسم الثلاثي", "الاسم الرباعي", "اسم المشارك بالعربي", "اسم الطالب",
            "Participant Full Name", "Full Name (English)", "First & Last Name", "English Name",
            "رقم الجوال", "رقم الهاتف", "رقم الواتساب للتواصل", "جوال ولي الأمر", "Mobile Number",
            "Phone Number", "Contact Phone (+966)", "WhatsApp No", "Cell Phone",
            "البريد الإلكتروني", "الايميل الشخصي", "البريد الجامعي", "إيميل الطالب الرسمي",
            "Email Address", "Personal Email", "Academic Email", "Student University Email",
            "رقم الهوية الوطنية", "رقم الإقامة", "National ID", "Iqama Number"
        ],
        "samples": [
            ["عبدالله محمد السالم", "فهد الدوسري", "سارة إبراهيم الشريف"],
            ["Salman Al-Harbi", "Nouf Al-Otaibi", "Tariq Al-Ali"],
            ["0501234567", "+966554433221", "00966541239876", "0567788990"],
            ["student@example.com", "participant@example.com", "admin@example.com"],
            ["fahad@example.com", "sarah99@example.com", "tariq.ali@example.com"],
            ["1098765432", "2198765432", "1122334455"]
        ]
    },
    "Structured/MetaData": {
        "headers": [
            "الرقم الجامعي", "رقم القيد الأكاديمي", "Student ID", "Academic ID No",
            "اسم الجامعة", "الجهة التعليمية", "جامعة التخرج", "University / College", "Institution",
            "التخصص الأكاديمي", "القسم العلمي", "الكلية", "Major", "Degree Program", "Department",
            "المستوى الدراسي", "السنة الأكاديمية", "المرحلة الدراسية", "Academic Level", "Year of Study",
            "الجنس", "نوع الجنس", "Gender", "Sex",
            "مدينة الإقامة", "المنطقة / الفرع", "المقر المفضل", "City / Branch", "Campus Location",
            "تاريخ التسجيل", "وقت الإرسال", "Submission Timestamp", "Registered At Date",
            "المعدل التراكمي", "درجة الاختبار", "GPA", "Evaluation Score",
            "رابط حساب لينكد إن", "الملف الشخصي", "LinkedIn URL", "GitHub Profile", "Portfolio Link"
        ],
        "samples": [
            ["441002938", "442001928", "443009182"],
            ["جامعة الملك عبدالعزيز", "جامعة جدة", "King Fahd University of Petroleum & Minerals"],
            ["علوم الحاسب", "الذكاء الاصطناعي", "هندسة البرمجيات", "نظم المعلومات"],
            ["سنة أولى", "سنة ثالثة", "خريج", "سنة امتياز", "ماجستير"],
            ["ذكر", "أنثى", "Male", "Female"],
            ["جدة", "الرياض", "الدمام", "مكة المكرمة"],
            ["2026-09-01 14:30:00", "2026-09-02 09:15:22", "46266.6125"],
            ["4.85 / 5.0", "3.90 / 4.0", "95.5%"],
            ["https://linkedin.com/in/fahad", "https://github.com/salman"]
        ]
    },
    "Categorical/MultiSelect": {
        "headers": [
            "هل توافق على الشروط والأحكام؟", "هل حضرت ورشة العمل السابقة؟", "هل أنت عضو في النادي؟",
            "Do you agree to terms?", "Have you attended previous workshops?", "Active Club Member?",
            "موافقة على التغطية الإعلامية والتصوير", "Consent to media coverage & photos",
            "حالة الحضور", "حاضر / غائب", "Attendance Status",
            "المهارات التقنية التي تجيدها", "مجالات الاهتمام المفضلة", "Technical Skills (Multi-select)",
            "أيام الحضور المفضلة", "اختر المسار التدريبي المناسب", "Preferred Tracks"
        ],
        "samples": [
            ["نعم", "لا", "نعم"],
            ["Yes", "No", "Yes"],
            ["موافق", "غير موافق"],
            ["حاضر", "غائب", "معتذر"],
            ["Python، Docker، SQL", "Pandas, Scikit-Learn, PyTorch", "Java; C++; SQL"],
            ["الأحد، الثلاثاء", "السبت فقط", "جميع الأيام"],
            ["مسار الذكاء الاصطناعي", "مسار هندسة البيانات", "مسار تحليل النظم"]
        ]
    },
    "Free-Form": {
        "headers": [
            "لماذا ترغب بالانضمام إلى هذا المعسكر؟", "ما هي دوافعك للتقديم؟", "Why do you want to join?",
            "ما هي تطلعاتك وأهدافك من البرنامج؟", "What are your expectations?",
            "صف أبرز التحديات التي واجهتك سابقاً", "Describe past technical challenges",
            "ما أكبر مسبب للتشتت الذهني أثناء العمل أو الدراسة؟", "Biggest distraction in daily work",
            "ملاحظات أو اقتراحات إضافية تود مشاركتها", "Additional Comments & Feedback",
            "General Feedback & Comments", "Feedback", "Comments", "Any suggestions or notes",
            "ملاحظات واقتراحات عامة", "مرئيات ومقترحات المشاركين", "مقترحات لتطوير الورشة",
            "تحدث باختصار عن مشروع تقني قمت ببنائه", "Tell us about a technical project you built",
            "Brief Project Summary", "Technical Background Details"
        ],
        "samples": [
            ["أرغب في تطوير مهاراتي العملية في بناء خطوط معالجة البيانات وتطبيق نماذج التعلم الآلي"],
            ["الاستفادة من خبرات المدربين والتواصل مع المجتمع التقني لبناء حلول وطنية تخدم رؤية 2030"],
            ["صعوبة التعامل مع البيانات غير المنظمة والتكرارات في ملفات الإكسل الضخمة"],
            ["وسائل التواصل الاجتماعي والإشعارات المتكررة أثناء فترات التركيز العميق"],
            ["نأمل توفير تسجيلات مرئية للورش وتوفير تمارين عملية مكثفة"],
            ["Great workshop overall, would love more hands-on practice with PyTorch and advanced pipeline modules."],
            ["Everything was clear and well organized, thanks to the instructors!"]
        ]
    }
}

# =====================================================================
# 2. Raw Data Harvesting & Ground-Truth Extraction
# =====================================================================

def extract_raw_dataset_examples(raw_dir: str = "RawData", config_dir: str = "config") -> List[Dict[str, Any]]:
    """
    Reads actual Excel workbooks from RawData/ and derives verified ground truth
    pairs from actual spreadsheet columns and respondent values.
    """
    from pipeline.contract_generator import AutoContractGenerator

    raw_examples = []
    
    # Load contracts for exact mapping lookups
    contracts = {}
    for c_file in ["developers_committee_contract.yaml", "workshop_contract.yaml"]:
        p = os.path.join(config_dir, c_file)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                c_data = yaml.safe_load(f)
                contracts[c_file] = c_data

    if not os.path.exists(raw_dir):
        print(f"[Warning] Raw directory '{raw_dir}' not found.")
        return []

    for fname in os.listdir(raw_dir):
        if not fname.lower().endswith(".xlsx"):
            continue

        fpath = os.path.join(raw_dir, fname)
        try:
            wb = openpyxl.load_workbook(fpath, data_only=True)
        except Exception as e:
            print(f"[Warning] Could not read {fname}: {e}")
            continue

        # Match contract if known
        matched_contract = None
        fname_lower = fname.lower()
        if any(k in fname_lower for k in ["committee", "مطورين", "لجنة"]):
            matched_contract = contracts.get("developers_committee_contract.yaml")
        elif any(k in fname_lower for k in ["workshop", "distraction", "تشتت"]):
            matched_contract = contracts.get("workshop_contract.yaml")

        for sname in wb.sheetnames:
            ws = wb[sname]
            all_rows = list(ws.iter_rows(values_only=True))
            if len(all_rows) < 2:
                continue

            headers = [str(h).strip() for h in all_rows[0] if h is not None]
            data_rows = all_rows[1:]

            for col_idx, raw_header in enumerate(headers):
                if not raw_header:
                    continue

                # Collect all real cell values for this column
                col_cells = []
                for r in data_rows:
                    if col_idx < len(r) and r[col_idx] is not None:
                        val_str = str(r[col_idx]).strip()
                        if val_str and val_str.lower() != "none":
                            col_cells.append(val_str)

                # Determine Ground-Truth Group Label
                target_group = None
                if matched_contract:
                    for m in matched_contract.get("canonical_mappings", []):
                        if raw_header == m.get("target_field") or raw_header in m.get("aliases", []):
                            target_group = m.get("group")
                            break

                # If not explicitly mapped in contract, use rule classifier
                if not target_group or target_group not in LABEL_MAP:
                    classification = AutoContractGenerator.classify_column(raw_header, col_cells[:5])
                    target_group = classification["group"]

                label_id = LABEL_MAP[target_group]

                # Generate base pair
                sample_preview = ", ".join(col_cells[:3]) if col_cells else ""
                raw_examples.append({
                    "header": raw_header,
                    "input_text": f"Header: {raw_header} | Samples: {sample_preview[:120]}",
                    "label": label_id,
                    "group": target_group,
                    "source": f"raw:{fname}:{sname}"
                })

                # Augment: Subsample permutations of real cell values
                if len(col_cells) >= 4:
                    for _ in range(4):
                        sampled_subset = random.sample(col_cells, k=min(3, len(col_cells)))
                        subset_str = ", ".join(sampled_subset)
                        raw_examples.append({
                            "header": raw_header,
                            "input_text": f"Header: {raw_header} | Samples: {subset_str[:120]}",
                            "label": label_id,
                            "group": target_group,
                            "source": f"raw_aug:{fname}"
                        })

                # Augment: Header variations (prefixes, suffixes, noise)
                header_variants = [
                    f"يرجى إدخال {raw_header}",
                    f"{raw_header} *",
                    f"حقل: {raw_header}",
                    raw_header.replace("؟", "").replace(":", "").strip()
                ]
                for variant in header_variants:
                    sub_str = ", ".join(random.sample(col_cells, k=min(2, len(col_cells)))) if col_cells else ""
                    raw_examples.append({
                        "header": variant,
                        "input_text": f"Header: {variant} | Samples: {sub_str[:120]}",
                        "label": label_id,
                        "group": target_group,
                        "source": f"raw_variant:{fname}"
                    })

                # Include raw header without samples for robust zero-sample inference
                raw_examples.append({
                    "header": raw_header,
                    "input_text": f"Header: {raw_header} | Samples: ",
                    "label": label_id,
                    "group": target_group,
                    "source": f"raw_no_samples:{fname}"
                })

    return raw_examples

def build_combined_training_dataset(samples_per_synthetic_class: int = 150) -> List[Dict[str, Any]]:
    """
    Merges real raw data harvested from RawData/ with synthetic template data.
    """
    raw_data = []  # Public demo: never harvest personal records for training.
    print(f"[Dataset] Harvested {len(raw_data)} real & augmented examples from RawData/ spreadsheets.")

    # Generate synthetic data for class balance (both with samples and without samples)
    synthetic_data = []
    for group_name, template in SYNTHETIC_TEMPLATES.items():
        headers = template["headers"]
        samples_pool = template["samples"]
        label_id = LABEL_MAP[group_name]

        for i in range(samples_per_synthetic_class):
            header = random.choice(headers)
            if i % 3 == 0:
                sample_preview = ""
            else:
                sample_list = random.choice(samples_pool)
                sample_preview = ", ".join(str(s)[:35] for s in sample_list[:3])

            synthetic_data.append({
                "header": header,
                "input_text": f"Header: {header} | Samples: {sample_preview}",
                "label": label_id,
                "group": group_name,
                "source": "synthetic_template"
            })

    combined = raw_data + synthetic_data
    random.shuffle(combined)
    print(f"[Dataset] Combined dataset ready: {len(combined)} total labeled training examples.")
    return combined

# =====================================================================
# 3. Model Training Engines
# =====================================================================

def train_sklearn_model(dataset: List[Dict[str, Any]], output_dir: str = "models"):
    """
    Trains an ultra-fast, high-precision Scikit-Learn TF-IDF + Logistic Regression
    sequence classifier with calibrated probability output (<1ms inference on CPU).
    Combines word-level and character-level n-grams for bilingual Arabic/English accuracy.
    """
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline, FeatureUnion
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report

    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "tfidf_column_classifier.joblib")

    texts = [d["input_text"] for d in dataset]
    labels = [d["label"] for d in dataset]

    # 80/20 train/test split with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.20, random_state=42, stratify=labels
    )

    print(f"\n[Scikit-Learn Training] Training TF-IDF Classifier on {len(X_train)} samples...")
    features = FeatureUnion([
        ("word_tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            analyzer="word",
            sublinear_tf=True,
            min_df=1
        )),
        ("char_tfidf", TfidfVectorizer(
            ngram_range=(2, 5),
            analyzer="char_wb",
            sublinear_tf=True,
            min_df=1
        ))
    ])

    pipeline = Pipeline([
        ("features", features),
        ("clf", LogisticRegression(
            C=10.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ))
    ])

    pipeline.fit(X_train, y_train)

    # Evaluation
    preds = pipeline.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"[Scikit-Learn Evaluation] Validation Accuracy: {acc * 100:.2f}%\n")
    print(classification_report(y_test, preds, target_names=[ID2LABEL[i] for i in range(len(LABEL_MAP))]))

    # Retrain on 100% of dataset for maximum production generalization
    pipeline.fit(texts, labels)
    joblib.dump(pipeline, model_path)
    print(f"[SUCCESS] Ultra-fast TF-IDF model saved to: {model_path} ({os.path.getsize(model_path) / 1024:.1f} KB)")
    return pipeline

def train_pytorch_transformer(
    dataset: List[Dict[str, Any]],
    output_dir: str = "models",
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    epochs: int = 3,
    batch_size: int = 16
):
    """
    Fine-tunes a PyTorch / Hugging Face Transformer Sequence Classifier
    directly without requiring external 'datasets' package.
    """
    try:
        import torch
        from torch.utils.data import Dataset, DataLoader
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError:
        print("[Notice] 'torch' or 'transformers' not installed. Skipping PyTorch training.")
        return

    save_dir = os.path.join(output_dir, "transformer_column_classifier")
    os.makedirs(save_dir, exist_ok=True)

    print(f"\n[PyTorch Training] Initializing base model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABEL_MAP),
        id2label=ID2LABEL,
        label2id=LABEL_MAP
    )

    texts = [d["input_text"] for d in dataset]
    labels = [d["label"] for d in dataset]

    class TorchColumnDataset(Dataset):
        def __init__(self, texts_list, labels_list, tok, max_len=128):
            self.encodings = tok(texts_list, padding="max_length", truncation=True, max_length=max_len, return_tensors="pt")
            self.labels = torch.tensor(labels_list, dtype=torch.long)

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            item = {k: v[idx] for k, v in self.encodings.items()}
            item["labels"] = self.labels[idx]
            return item

    # 80/20 train/test split
    split_idx = int(len(texts) * 0.8)
    train_ds = TorchColumnDataset(texts[:split_idx], labels[:split_idx], tokenizer)
    val_ds = TorchColumnDataset(texts[split_idx:], labels[split_idx:], tokenizer)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5)

    print(f"[PyTorch Training] Fine-tuning on {len(train_ds)} samples on device: {device}...")
    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            batch_labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=batch_labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / max(1, len(train_loader))
        print(f"  Epoch {epoch + 1}/{epochs} - Average Loss: {avg_loss:.4f}")

    # Validation
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            batch_labels = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=1)
            correct += (preds == batch_labels).sum().item()
            total += len(batch_labels)

    val_acc = (correct / total) * 100 if total > 0 else 0.0
    print(f"[PyTorch Evaluation] Validation Accuracy: {val_acc:.2f}%")

    # Save fine-tuned model and tokenizer
    print(f"[PyTorch Save] Saving fine-tuned Transformer model to -> {save_dir}")
    model.save_pretrained(save_dir)
    tokenizer.save_pretrained(save_dir)
    print(f"[SUCCESS] Transformer weights saved cleanly to: {save_dir}")

# =====================================================================
# 4. CLI Main
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Transformer NLP Classifier Training Pipeline on Raw Data")
    parser.add_argument("--train", action="store_true", help="Train models on raw data and save weights")
    parser.add_argument("--fast-only", action="store_true", help="Train only the ultra-fast Scikit-Learn TF-IDF model")
    parser.add_argument("--output-dir", default="models", help="Output directory for saved model artifacts")
    parser.add_argument("--output-json", default="tools/raw_and_synthetic_dataset.json", help="Path to save harvested dataset JSON")
    parser.add_argument("--generate-dataset-only", action="store_true", help="Harvest and save dataset only without training")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs for PyTorch model")
    parser.add_argument("--samples-per-synthetic-class", type=int, default=100, help="Synthetic balance samples per class")

    args = parser.parse_args()

    print("=" * 75)
    print("   NLP COLUMN CLASSIFIER - TRAINING PIPELINE ON REAL RAW DATA")
    print("=" * 75)

    dataset = build_combined_training_dataset(samples_per_synthetic_class=args.samples_per_synthetic_class)

    if args.output_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"[Dataset] Saved harvested dataset to: {args.output_json}")

    if args.generate_dataset_only:
        print("[Done] Dataset extraction complete.")
        return

    # Train ultra-fast Scikit-Learn TF-IDF model
    train_sklearn_model(dataset, output_dir=args.output_dir)

    # Train PyTorch Transformer model unless fast-only is requested
    if not args.fast_only:
        train_pytorch_transformer(dataset, output_dir=args.output_dir, epochs=args.epochs)

    print("\n[Done] All requested models trained and exported successfully.")

if __name__ == "__main__":
    main()
