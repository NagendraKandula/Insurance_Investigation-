
from collections import defaultdict


class Evaluator:

    def __init__(self, threshold=40):
        self.threshold = threshold

    @staticmethod
    def normalize_entity_type(entity_type):
        return str(entity_type).strip().lower()

    def evaluate(self, risk_results, ground_truth):

        print("\n========== FRAUD DETECTION EVALUATION ==========")

        # --------------------------------------------------
        # 1. Convert risk results into a lookup dictionary
        # --------------------------------------------------

        predictions = {}

        for result in risk_results:

            key = (
                self.normalize_entity_type(result["entity_type"]),
                result["entity_id"]
            )

            predictions[key] = result

        # --------------------------------------------------
        # 2. Initialize evaluation counters
        # --------------------------------------------------

        counts = {
            "TP": 0,
            "FP": 0,
            "TN": 0,
            "FN": 0
        }

        pattern_counts = defaultdict(
            lambda: {
                "TP": 0,
                "FP": 0,
                "TN": 0,
                "FN": 0
            }
        )

        detected_suspicious_networks = defaultdict(int)
        total_suspicious_networks = defaultdict(int)

        # --------------------------------------------------
        # 3. Evaluate each ground-truth record
        # --------------------------------------------------

        detailed_results = []

        for truth in ground_truth:

            entity_type = self.normalize_entity_type(
                truth["entity_type"]
            )

            entity_id = truth["entity_id"]
            expected_label = truth["expected_label"].upper()
            pattern_type = truth["pattern_type"]
            network_id = truth["planted_network_id"]

            key = (entity_type, entity_id)

            prediction = predictions.get(key)

            risk_score = (
                prediction["risk_score"]
                if prediction else 0
            )

            predicted_label = (
                "SUSPICIOUS"
                if risk_score >= self.threshold
                else "BENIGN"
            )

            # ----------------------------------------------
            # 4. Confusion matrix classification
            # ----------------------------------------------

            if expected_label == "SUSPICIOUS":

                if network_id:
                    total_suspicious_networks[network_id] += 1

                if predicted_label == "SUSPICIOUS":
                    counts["TP"] += 1
                    pattern_counts[pattern_type]["TP"] += 1

                    if network_id:
                        detected_suspicious_networks[network_id] += 1

                else:
                    counts["FN"] += 1
                    pattern_counts[pattern_type]["FN"] += 1

            elif expected_label == "BENIGN":

                if predicted_label == "SUSPICIOUS":
                    counts["FP"] += 1
                    pattern_counts[pattern_type]["FP"] += 1

                else:
                    counts["TN"] += 1
                    pattern_counts[pattern_type]["TN"] += 1

            detailed_results.append({
                "entity_type": entity_type,
                "entity_id": entity_id,
                "pattern_type": pattern_type,
                "planted_network_id": network_id,
                "expected_label": expected_label,
                "predicted_label": predicted_label,
                "risk_score": risk_score,
                "correct": expected_label == predicted_label
            })

        # --------------------------------------------------
        # 5. Calculate metrics
        # --------------------------------------------------

        tp = counts["TP"]
        fp = counts["FP"]
        tn = counts["TN"]
        fn = counts["FN"]

        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0

        f1_score = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) else 0
        )

        accuracy = (
            (tp + tn) / (tp + tn + fp + fn)
            if (tp + tn + fp + fn) else 0
        )

        # --------------------------------------------------
        # 6. Print overall evaluation
        # --------------------------------------------------

        print("\n========== CONFUSION MATRIX ==========")

        print(f"True Positives  : {tp}")
        print(f"False Positives : {fp}")
        print(f"True Negatives  : {tn}")
        print(f"False Negatives : {fn}")

        print("\n========== OVERALL METRICS ==========")

        print(f"Threshold : {self.threshold}")
        print(f"Precision : {precision:.4f}")
        print(f"Recall    : {recall:.4f}")
        print(f"F1 Score  : {f1_score:.4f}")
        print(f"Accuracy  : {accuracy:.4f}")

        # --------------------------------------------------
        # 7. Pattern-wise evaluation
        # --------------------------------------------------

        print("\n========== PATTERN-WISE EVALUATION ==========")

        pattern_metrics = {}

        for pattern, values in sorted(pattern_counts.items()):

            p_tp = values["TP"]
            p_fp = values["FP"]
            p_fn = values["FN"]
            p_tn = values["TN"]

            p_precision = (
                p_tp / (p_tp + p_fp)
                if (p_tp + p_fp) else 0
            )

            p_recall = (
                p_tp / (p_tp + p_fn)
                if (p_tp + p_fn) else 0
            )

            p_f1 = (
                2 * p_precision * p_recall /
                (p_precision + p_recall)
                if (p_precision + p_recall) else 0
            )

            pattern_metrics[pattern] = {
                **values,
                "precision": p_precision,
                "recall": p_recall,
                "f1_score": p_f1
            }

            print(f"\nPattern: {pattern}")
            print(f"TP: {p_tp} | FP: {p_fp} | TN: {p_tn} | FN: {p_fn}")
            print(f"Precision: {p_precision:.4f}")
            print(f"Recall   : {p_recall:.4f}")
            print(f"F1 Score : {p_f1:.4f}")

        # --------------------------------------------------
        # 8. Suspicious network detection summary
        # --------------------------------------------------

        print("\n========== NETWORK DETECTION SUMMARY ==========")

        network_results = []

        for network_id, total in sorted(total_suspicious_networks.items()):

            detected = detected_suspicious_networks[network_id]

            detection_rate = detected / total if total else 0

            network_results.append({
                "network_id": network_id,
                "total_entities": total,
                "detected_entities": detected,
                "detection_rate": detection_rate
            })

        network_results.sort(
            key=lambda item: item["detection_rate"],
            reverse=True
        )

        for network in network_results:

            print(
                f"{network['network_id']} | "
                f"Detected: {network['detected_entities']}/"
                f"{network['total_entities']} | "
                f"Detection rate: "
                f"{network['detection_rate']:.2%}"
            )

        # --------------------------------------------------
        # 9. Return structured evaluation report
        # --------------------------------------------------

        return {
            "threshold": self.threshold,
            "confusion_matrix": counts,
            "metrics": {
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "accuracy": accuracy
            },
            "pattern_metrics": pattern_metrics,
            "network_results": network_results,
            "detailed_results": detailed_results
        }
