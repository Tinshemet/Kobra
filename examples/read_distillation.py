"""Offline demonstration with an authored response, not a real model prediction."""

from kobra import (
    ClientConfig,
    DistillingReader,
    DomainVocabulary,
    EnglishFrontDoor,
    Request,
    Services,
)


class RecordedProposal:
    def complete(self, *, prompt, text, schema):
        if text != "Compare the reports. Do not send them.":
            raise ValueError("No recorded proposal for this input")
        return {
            "points": [
                {
                    "sentence": "The user requests a comparison of the reports.",
                    "evidence": [{"quote": "Compare the reports.", "occurrence": 0}],
                    "links": [],
                    "uncertainty": [],
                },
                {
                    "sentence": "The user prohibits sending the reports.",
                    "evidence": [{"quote": "Do not send them.", "occurrence": 0}],
                    "links": [
                        {
                            "target": 0,
                            "relationship": "constrains handling of the same reports",
                        }
                    ],
                    "uncertainty": [],
                },
            ]
        }


def main():
    request = Request("um, Compare the reports. Do not send them.")
    front = EnglishFrontDoor(
        DomainVocabulary(
            nouns=frozenset({"report", "reports"}),
            operations=frozenset({"compare", "send"}),
        )
    )
    services = Services(ClientConfig("document-demo", "1"), model=RecordedProposal())
    view = front.normalize(request, services)
    result = DistillingReader(vocabulary=front.vocabulary).read(view, request, services)
    print("Authored response demonstration; semantic accuracy has not been evaluated.")
    for point in result.distillation.points:
        print(f"{point.id}: {point.sentence}")
        for span in point.evidence:
            print(f"  Original evidence: {request.text[span.start : span.end]!r}")


if __name__ == "__main__":
    main()
