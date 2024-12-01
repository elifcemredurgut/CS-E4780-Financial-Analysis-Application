import pandas as pd

SYSTEM_EMA_PATH = "./system/ema.csv"
ACTUAL_EMA_PATH = "./actual/ema.csv"

SYSTEM_BREAKOUT_PATH = "./system/breakout.csv"
ACTUAL_BREAKOUT_PATH = "./actual/breakout.csv"


accuracy_df = pd.DataFrame()

tp = 0
fp = 0
tn = 0
fn = 0

system_breakout_df = pd.read_csv(SYSTEM_BREAKOUT_PATH)
actual_breakout_df = pd.read_csv(ACTUAL_BREAKOUT_PATH)

merged_df = pd.merge(actual_breakout_df, system_breakout_df, on=["stock_id","dt"], how='left',  suffixes=("_actual", "_system"))
merged_df["is_match"] = (
    (merged_df["stock_id"] == merged_df["stock_id"]) &
    (merged_df["dt"] == merged_df["dt"]) &
    (merged_df["breakout_type_system"] == merged_df["breakout_type_actual"])
)

# Precision and Recall for Breakout
tp_breakout = merged_df["is_match"].sum()
fp_breakout = (~merged_df["is_match"] & ~merged_df["breakout_type_actual"].isna()).sum()
fn_breakout = merged_df["breakout_type_actual"].isna().sum()


precision_breakout = tp_breakout / (tp_breakout + fp_breakout) if (tp_breakout + fp_breakout) > 0 else 0
recall_breakout = tp_breakout / (tp_breakout + fn_breakout) if (tp_breakout + fn_breakout) > 0 else 0
f1_score = (2*precision_breakout*recall_breakout)/(precision_breakout+recall_breakout)

print(f"True Positives:{tp_breakout}\nFalse Positives:{fp_breakout}\nFalse Negatives:{fn_breakout}\nPrecision: {precision_breakout:.2f}\nRecall: {recall_breakout:.2f}\nF1 Score:{f1_score}")
