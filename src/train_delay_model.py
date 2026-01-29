from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype

from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
import joblib

DB_DEFAULT = "flight_delay.duckdb"
VIEW_DEFAULT = "v_feature_model"


def pick_threshold_max_f1(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    precision, recall, threshold = precision_recall_curve(y_true, y_prob)
    # precision/recall têm len = len(threshold)+1
    f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    best_idx = int(np.nanargmax(f1)) if len(f1) else 0
    return {
        "threshold": float(threshold[best_idx]) if len(threshold) else 0.5,
        "precision": float(precision[best_idx]) if len(precision) else float("nan"),
        "recall": float(recall[best_idx]) if len(recall) else float("nan"),
        "f1": float(f1[best_idx]) if len(f1) else float("nan"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--view", default=VIEW_DEFAULT)
    ap.add_argument("--out_dir", default="models")
    ap.add_argument("--time_col", default="sched_dep_ts")
    ap.add_argument("--train_frac", type=float, default=0.8)
    ap.add_argument("--random_state", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(args.db)
    df = con.execute(f"SELECT * FROM {args.view}").df()
    con.close()

    required = {"y_delayed_15", args.time_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns in {args.view}: {sorted(missing)}. "
            f"Update the SQL view to include them."
        )

    # Basic cleanup
    df = df.dropna(subset=[args.time_col, "y_delayed_15"]).copy()
    df[args.time_col] = pd.to_datetime(df[args.time_col], errors="coerce")
    df = df.dropna(subset=[args.time_col]).sort_values(args.time_col)

    y = df["y_delayed_15"].astype(int).to_numpy()

    drop_cols = {"y_delayed_15", args.time_col}
    X = df[[c for c in df.columns if c not in drop_cols]].copy()

    # Columns split
    cat_cols = []
    num_cols = []
    for c in X.columns:
        if is_datetime64_any_dtype(X[c]):
            cat_cols.append(c)
        elif is_numeric_dtype(X[c]):
            num_cols.append(c)
        else:
            cat_cols.append(c)

    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
    ])

    pre = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, num_cols),
            ("cat", categorical_pipe, cat_cols),
        ],
        remainder="drop",
    )

    clf = LogisticRegression(
        C = 0.3,
        max_iter=2000,
        class_weight="balanced",
        n_jobs=None,
        random_state=args.random_state,
    )

    pipe = Pipeline([
        ("pre", pre),
        ("clf", clf),
    ])

    # Time split (no leakage)
    n = len(df)
    split_idx = int(n * args.train_frac)

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    pipe.fit(X_train, y_train)

    y_prob = pipe.predict_proba(X_test)[:, 1]

    # Metrics
    roc_auc = float(roc_auc_score(y_test, y_prob))
    pr_auc = float(average_precision_score(y_test, y_prob))

    y_pred_05 = (y_prob >= 0.5).astype(int)

    best = pick_threshold_max_f1(y_test, y_prob)
    y_pred_best = (y_prob >= best["threshold"]).astype(int)

    metrics = {
        "data": {
            "n_total": int(n),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "delay_rate_total": float(y.mean()),
            "delay_rate_train": float(y_train.mean()),
            "delay_rate_test": float(y_test.mean()),
            "time_col": args.time_col,
            "train_frac": float(args.train_frac),
            "view": args.view,
            "db": args.db,
        },
        "metrics": {
            "pr_auc": pr_auc,
            "roc_auc": roc_auc,
            "threshold_0_5": {
                "confusion_matrix": confusion_matrix(y_test, y_pred_05).tolist(),
                "report": classification_report(y_test, y_pred_05, output_dict=True),
            },
            "best_f1_threshold": {
                **best,
                "confusion_matrix": confusion_matrix(y_test, y_pred_best).tolist(),
                "report": classification_report(y_test, y_pred_best, output_dict=True),
            },
        },
        "features": {
            "categorical": cat_cols,
            "numeric": num_cols,
        },
    }

    model_path = out_dir / "delay_lr_pipeline.joblib"
    metrics_path = out_dir / "delay_lr_metrics.json"

    joblib.dump(pipe, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved:", model_path)
    print("Saved:", metrics_path)
    print("\nPR-AUC:", pr_auc)
    print("ROC-AUC:", roc_auc)
    print("BEST F1 threshold:", best)


if __name__ == "__main__":
    main()
