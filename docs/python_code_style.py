"""
The beginning of any python code file should contain a brief description of the file's purpose,
and an example of usage, if applicable. It should be relatively short, but informative, and
should provide enough context for someone skimming files to understand its intent and how to use it.

This particular file is a Python code style guide that outlines conventions and practices for 
writing clean, maintainable, and readable Python code.
"""

"""
Python Code Style Guide
------------------------------------------------------------------------------
This file follows the base of PEP 8 with modern extensions, plus the following
specific conventions:

Method Delimiters:
   - Each method is preceded by an 80-character-long line of '#' characters
     to visually separate and emphasize method boundaries.

Assignment Alignment:
   - Consecutive assignment statements align the '=' signs vertically
     to improve visual structure and readability.

Dictionary Alignment:
   - In dictionary definitions, consecutive key-value pairs at the same nesting level
     should have their colons (':') vertically aligned to enhance readability.

Parameter Alignment:
   - When defining methods with multiple parameters, vertically align:
     * Parameter names
     * Colons (':') before type annotations
     * Equal signs ('=') before default values
   - This creates a clean, tabular structure that makes parameter lists easier to read.

Typing and Docstrings:
   - Full type hints are used for all arguments and return types.
   - Public methods include docstrings following Google-style formatting.

Constants:
   - Class-level constants are written in UPPER_CASE (e.g., INTEREST_RATE).
   - Never hardcode any literal values in the code; use constants instead.
   - All paths need to be constructed relative to the project root directory (use src/luciqr/utils/project.py). Never use absolute paths.
   - Group related constants together with meaningful section comments.

Private/Internal Methods:
   - Internal helper methods are prefixed with a single underscore.

Exceptions:
   - Custom exceptions inherit from `Exception` and use descriptive names.
   - Include meaningful error messages with context about what went wrong.
   - Consider creating exception hierarchies for related error types.

Date & Time:
   - All timestamps use `datetime.datetime.now(datetime.UTC)` (Python 3.11+) or `datetime.datetime.utcnow()` for consistency.
   - Always store timestamps in UTC and convert for display only.

Representation:
   - `__repr__` is implemented for debugging and logging readability.

Readability Over Brevity:
   - The formatting intentionally prioritizes clarity over compactness.
   - Line lengths are kept within ~88 characters as per Black's default.

Imports:
   - Group imports in order: standard library, third-party, local/project
   - Use absolute imports for clarity
   - Sort imports alphabetically within each group

Error Handling:
   - Use specific exceptions rather than bare except clauses
   - Log errors appropriately before re-raising
   - Provide context in error messages

Testing:
   - Test method names should describe what is being tested
   - Use descriptive assertion messages
   - Follow AAA pattern: Arrange, Act, Assert
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

################################################################################

class InvalidTransactionError(Exception):
    """Exception raised for invalid transactions."""
    pass

################################################################################

class Account:
    """A simple bank account model."""

    # Financial constants
    INTEREST_RATE         = 0.015  # Annual interest rate (1.5%)
    MIN_BALANCE           = 0.0    # Minimum allowed balance
    MAX_WITHDRAWAL_LIMIT  = 10000  # Maximum single withdrawal

    ################################################################################

    def __init__(
        self, 
        owner   : str   = "Anonymous", 
        balance : float = 0.0,
        currency: str   = "USD"
    ) -> None:
        """
        Initialize a new account.

        Args:
            owner: The name of the account holder.
            balance: The initial account balance (default is 0.0).
            currency: The currency code for this account.
        """
        self.owner            = owner
        self._balance         = balance
        self._currency        = currency
        self._created_at      = datetime.datetime.utcnow()
        self._transactions: list[tuple[datetime.datetime, str, float]] = []
        
        # Example of dictionary with aligned colons
        self._account_info = {
            "owner"           : owner,
            "balance"         : balance,
            "currency"        : currency,
            "creation_date"   : self._created_at,
            "account_type"    : "Standard",
            "interest_rate"   : self.INTEREST_RATE
        }

    ################################################################################

    def deposit(self, amount: float) -> None:
        """
        Deposit money into the account.

        Args:
            amount: The amount to deposit.

        Raises:
            InvalidTransactionError: If the amount is not positive.
        """
        if amount <= 0:
            raise InvalidTransactionError(
                f"Deposit amount must be positive, got {amount}"
            )

        self._balance += amount
        self._record_transaction("deposit", amount)

    ################################################################################

    def withdraw(self, amount: float) -> None:
        """
        Withdraw money from the account.

        Args:
            amount: The amount to withdraw.

        Raises:
            InvalidTransactionError: If the amount exceeds the current balance.
        """
        if amount > self._balance:
            raise InvalidTransactionError(
                f"Insufficient funds: requested {amount}, available {self._balance}"
            )

        self._balance -= amount
        self._record_transaction("withdraw", -amount)

    ################################################################################

    def get_balance(self) -> float:
        """Return the current balance."""
        return self._balance

    ################################################################################

    def generate_statement(
        self,
        include_details : bool = True,
        format_type     : str  = "plain",
        max_entries     : int  = 10
    ) -> str:
        """
        Return a formatted account statement.
        
        Args:
            include_details: Whether to include transaction details.
            format_type: Output format ("plain", "html", or "json").
            max_entries: Maximum number of transactions to include.
        
        Returns:
            A multiline string showing all transactions and final balance.
        """
        # Example of nested dictionary with aligned colons at each level
        format_options = {
            "plain" : {
                "header"      : f"Account Statement for {self.owner}",
                "separator"   : "-" * 40,
                "date_format" : "%Y-%m-%d %H:%M:%S",
                "alignment"   : "right"
            },
            "html"  : {
                "header"      : f"<h1>Account Statement for {self.owner}</h1>",
                "separator"   : "<hr/>",
                "date_format" : "%Y-%m-%d %H:%M:%S",
                "alignment"   : "left"
            }
        }
        
        options = format_options.get(format_type, format_options["plain"])
        
        lines = [
            options["header"],
            options["separator"],
        ]

        if include_details:
            transactions = self._transactions[-max_entries:] if max_entries > 0 else self._transactions
            for timestamp, tx_type, amount in transactions:
                time_str = timestamp.strftime(options["date_format"])
                lines.append(f"{time_str}  {tx_type.capitalize():<10} {amount:>10.2f}")

        lines.append(options["separator"])
        lines.append(f"Final Balance: {self._balance:.2f} {self._currency}")
        return "\n".join(lines)

    ################################################################################

    def apply_annual_interest(self) -> None:
        """Apply annual interest to the account."""
        interest      = self._balance * self.INTEREST_RATE
        self._balance += interest
        self._record_transaction("interest", interest)

    ################################################################################

    def created_at(self) -> datetime.datetime:
        """Return the creation timestamp of the account."""
        return self._created_at

    ################################################################################

    def __repr__(self) -> str:
        return f"<Account(owner={self.owner!r}, balance={self._balance:.2f})>"

    ################################################################################
    
    def _record_transaction(
        self, 
        tx_type : str, 
        amount  : float
    ) -> None:
        """Record a transaction in the internal ledger."""
        self._transactions.append(
            (datetime.datetime.utcnow(), tx_type, amount)
        )
