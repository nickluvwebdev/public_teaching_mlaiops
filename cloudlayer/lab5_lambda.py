"""Standard-library scoring of the exact managed logistic-model weights."""

import json
import math
import os
import boto3

MODEL = None


def handler(payload, context):
    global MODEL
    if MODEL is None:
        raw = (
            boto3.client("s3")
            .get_object(Bucket=os.environ["MODEL_BUCKET"], Key=os.environ["MODEL_KEY"])["Body"]
            .read()
        )
        MODEL = json.loads(raw)
    z = MODEL["intercept"]
    for name, mean, scale, coefficient in zip(
        MODEL["features"], MODEL["mean"], MODEL["scale"], MODEL["coefficients"]
    ):
        value = float(payload[name])
        if not math.isfinite(value):
            raise ValueError("Nonfinite input")
        z += ((value - mean) / scale) * coefficient
    probability = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
    return {"probability": probability, "model_version": os.environ["MODEL_VERSION"]}
