# Evaluation Metrics and Protocol

Run the benchmark with one command:

    cited-rag eval --golden eval/golden.jsonl

Three metrics are reported. Recall@5 is the fraction of
questions whose expected document appears in the top-5
chunks. Release target is Recall@5 >= 0.80.

MRR (Mean Reciprocal Rank) averages 1/rank of the first
relevant chunk across questions. Release target is MRR >= 0.60.
A question whose expected document ranks 2nd contributes 0.5.

Correct-refusal rate is the fraction of out-of-corpus
questions that trigger `Insufficient evidence`. Target is
>= 0.90. The eval command reproduces all three numbers
deterministically from the golden file.
