import os, re, joblib 
import pandas as pd   
import nltk                      
from nltk.corpus import stopwords    
from nltk.stem import PorterStemmer   
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score 

# Download stopwords silently (used for filtering out common words)
nltk.download("stopwords", quiet=True)

# Set up stopword list and stemmer
stop_words = set(stopwords.words("english"))
stemmer    = PorterStemmer()

# Function to clean a single text sample
def clean_text(s: str) -> str:
    s = s.lower()                                 # Convert to lowercase
    s = re.sub(r"<[^>]+>", " ", s)                # Remove HTML tags
    s = re.sub(r"[^a-z0-9\s]", " ", s)            # Remove punctuation/symbols
    toks = [w for w in s.split() if len(w) > 2]   # Remove short words (length <= 2)
    toks = [stemmer.stem(w) for w in toks if w not in stop_words]  # Remove stopwords and apply stemming
    return " ".join(toks)                         # Return cleaned text

# Function to clean a list of texts
def clean_texts(texts):
    """Batch-cleaner for the FunctionTransformer step."""
    return [clean_text(t) for t in texts]

PIPELINE_PATH = "spam_pipeline.pkl"
if not os.path.exists(PIPELINE_PATH):
    raise FileNotFoundError(f"Could not find {PIPELINE_PATH} in cwd")
model = joblib.load(PIPELINE_PATH)

################################################################################

print("\n=== Sample Predictions ===")

samples = [
    "Hey Sarah, are we still on for dinner tomorrow?",
    "Congratulations! You’ve been selected to win a brand new iPhone. Click here!",
]

# Remove non-ASCII characters from sample texts
safe = [s.encode("ascii", errors="ignore").decode() for s in samples]

# Predict probabilities for each class (column 1 is the SPAM probability)
probas = model.predict_proba(samples)[:, 1]

# Classify as SPAM if probability >= 0.7, else HAM
preds = (probas >= 0.7).astype(int)

for text, p, prob in zip(safe, preds, probas):
    tag = "SPAM" if p else "HAM "
    print(f"[{tag}] {prob:.3f} {text}")

################################################################################

print("\n=== Full Dataset Evaluation ===")

CSV_PATH = "email_text.csv"
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"Could not find {CSV_PATH} in cwd")

df = pd.read_csv(CSV_PATH)

# Keep only the first two columns (label and text)
if df.shape[1] > 2:
    df = df.iloc[:, :2]
df.columns = ["label", "text"]

# Remove missing or empty text rows
df = df.dropna(subset=["text"])
df["text"] = df["text"].astype(str).str.strip()
df = df[df["text"] != ""]

# Label normalization function
def to_binary(label):
    """
    Converts label to binary:
    - 1 for spam (e.g., 'spam', 'junk', 1, True)
    - 0 for ham  (e.g., 'ham', 'normal', 0, False)
    - None for unrecognized
    """
    if pd.isna(label):
        return None
    if label in (1, "1", True):
        return 1
    if label in (0, "0", False):
        return 0
    lab = str(label).strip().lower()
    if lab in {"spam", "junk", "unsolicited"}:
        return 1
    if lab in {"ham", "legit", "normal"}:
        return 0
    return None 

# Apply binary conversion
df["label"] = df["label"].apply(to_binary)
df = df.dropna(subset=["label"])

if df.empty:
    raise ValueError("After label-mapping no rows remain. Check the label values in email_text.csv!")

df["label"] = df["label"].astype(int)

y_true = df["label"]
texts  = df["text"].tolist()

# Make predictions on full dataset
y_pred  = model.predict(texts)              
y_proba = model.predict_proba(texts)[:, 1]  

print("\n-- Classification Report --")
print(classification_report(y_true, y_pred, digits=4))

print("-- Confusion Matrix --")
print(confusion_matrix(y_true, y_pred))

print(f"\nROC-AUC: {roc_auc_score(y_true, y_proba):.4f}")