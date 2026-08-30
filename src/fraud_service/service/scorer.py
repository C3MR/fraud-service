from dataclasses import dataclass

from fraud_service.domain.entities import Decision, Transaction
from fraud_service.domain.policies import decide
from fraud_service.service.interfaces import Model


@dataclass
class FraudScorer:
    model: Model
    block_threshold: float

    def score(self, txn: Transaction) -> Decision:
        features = txn.to_features()
        probability = self.model.predict_proba(features)
        return decide(probability, self.block_threshold)