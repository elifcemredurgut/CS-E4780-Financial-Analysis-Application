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

def format_timestamp(timestamp):
    if '.' in timestamp:
        time_part, microsecond_part = timestamp.split('.')
        microsecond_part = microsecond_part.ljust(6, '0') 
        return f"{time_part}.{microsecond_part}"
    else:
        return f"{timestamp}.000000" 

# Padding zero's in the end of the timestamp to match
system_breakout_df['dt'] = system_breakout_df['dt'].apply(format_timestamp)
actual_breakout_df['dt'] = actual_breakout_df['dt'].apply(format_timestamp)

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
f1_score = (2*precision_breakout*recall_breakout)/(precision_breakout+recall_breakout) if (precision_breakout+recall_breakout) > 0 else 0

print(f"True Positives:{tp_breakout}\nFalse Positives:{fp_breakout}\nFalse Negatives:{fn_breakout}\nPrecision: {precision_breakout:.2f}\nRecall: {recall_breakout:.2f}\nF1 Score:{f1_score}")

false_positives_df = merged_df[~merged_df["is_match"] & ~merged_df["breakout_type_actual"].isna()]
print("False Positives:")
print(false_positives_df[["stock_id", "dt", "breakout_type_system", "breakout_type_actual"]])