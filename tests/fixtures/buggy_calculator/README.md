# Buggy Calculator Fixture

This directory is copied into a temporary Git repository by tests. `calculator.py` intentionally divides by zero when the divisor is zero. `fix.patch` is a manually prepared valid patch. LACE validates it but does not execute this fixture in Milestone 1.

