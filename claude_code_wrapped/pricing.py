"""Pricing data and cost calculation for Claude models.

Based on official Anthropic pricing as of December 2025.
Source: https://docs.anthropic.com/en/docs/about-claude/models
"""

from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Pricing for a Claude model in USD per million tokens."""
    input_cost: float  # Base input tokens
    output_cost: float  # Output tokens
    cache_write_cost: float  # 5-minute cache writes (1.25x input)
    cache_read_cost: float  # Cache hits & refreshes (0.1x input)


# Official Anthropic pricing as of December 2025 (USD per million tokens)
# Source: https://platform.claude.com/docs/en/about-claude/pricing
MODEL_PRICING: dict[str, ModelPricing] = {
    # Claude 4.x models
    "claude-opus-4-5-20251101": ModelPricing(5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-20250514": ModelPricing(15.0, 75.0, 18.75, 1.50),
    "claude-opus-4-1-20250620": ModelPricing(15.0, 75.0, 18.75, 1.50),
    "claude-sonnet-4-5-20250514": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-sonnet-4-20250514": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-haiku-4-5-20251101": ModelPricing(1.0, 5.0, 1.25, 0.10),

    # Claude 3.x models
    "claude-3-5-sonnet-20241022": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-3-5-sonnet-20240620": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.0, 1.0, 0.08),
    "claude-3-opus-20240229": ModelPricing(15.0, 75.0, 18.75, 1.50),
    "claude-3-sonnet-20240229": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-3-haiku-20240307": ModelPricing(0.25, 1.25, 0.30, 0.03),
}

# Simplified model name mappings for display
MODEL_FAMILY_PRICING: dict[str, ModelPricing] = {
    "opus": ModelPricing(15.0, 75.0, 18.75, 1.50),  # Conservative estimate
    "sonnet": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "haiku": ModelPricing(0.80, 4.0, 1.0, 0.08),  # Use 3.5 Haiku as default
}


def get_model_pricing(model_name: str | None) -> ModelPricing | None:
    """Get pricing for a model by name.

    Handles both full model IDs and simplified names like 'Opus', 'Sonnet', 'Haiku'.
    """
    if not model_name:
        return None

    model_lower = model_name.lower()

    # Try exact match first
    if model_lower in MODEL_PRICING:
        return MODEL_PRICING[model_lower]

    # For simple names like "Opus", "Sonnet", "Haiku", use family pricing
    # This is what we get from the stats module's simplified model names
    for family, pricing in MODEL_FAMILY_PRICING.items():
        if model_lower == family:
            return pricing

    # Try partial match on full model IDs (for full model names like "claude-3-5-sonnet-...")
    for model_id, pricing in MODEL_PRICING.items():
        if model_lower in model_id or model_id in model_lower:
            return pricing

    # Fall back to family-based pricing for partial matches
    for family, pricing in MODEL_FAMILY_PRICING.items():
        if family in model_lower:
            return pricing

    return None


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    model_name: str | None = None,
) -> float | None:
    """Calculate cost in USD for a given token usage.

    Args:
        input_tokens: Number of input tokens (excluding cache)
        output_tokens: Number of output tokens
        cache_creation_tokens: Number of cache write tokens
        cache_read_tokens: Number of cache read tokens
        model_name: Model name or ID for pricing lookup

    Returns:
        Cost in USD, or None if pricing unavailable
    """
    pricing = get_model_pricing(model_name)
    if not pricing:
        return None

    # Convert to millions and calculate
    cost = (
        (input_tokens / 1_000_000) * pricing.input_cost +
        (output_tokens / 1_000_000) * pricing.output_cost +
        (cache_creation_tokens / 1_000_000) * pricing.cache_write_cost +
        (cache_read_tokens / 1_000_000) * pricing.cache_read_cost
    )

    return cost


def calculate_total_cost_by_model(
    model_usage: dict[str, dict[str, int]]
) -> tuple[float, dict[str, float]]:
    """Calculate total cost across all models.

    Args:
        model_usage: Dict mapping model names to token counts:
            {
                "Sonnet": {"input": 1000, "output": 500, "cache_create": 0, "cache_read": 0},
                "Opus": {"input": 500, "output": 200, ...},
            }

    Returns:
        Tuple of (total_cost, per_model_costs)
    """
    total = 0.0
    per_model: dict[str, float] = {}

    for model_name, tokens in model_usage.items():
        cost = calculate_cost(
            input_tokens=tokens.get("input", 0),
            output_tokens=tokens.get("output", 0),
            cache_creation_tokens=tokens.get("cache_create", 0),
            cache_read_tokens=tokens.get("cache_read", 0),
            model_name=model_name,
        )
        if cost is not None:
            per_model[model_name] = cost
            total += cost

    return total, per_model


def format_cost(cost: float | None) -> str:
    """Format cost for display."""
    if cost is None:
        return "N/A"
    if cost < 0.01:
        return f"${cost:.4f}"
    if cost < 1:
        return f"${cost:.2f}"
    if cost < 100:
        return f"${cost:.2f}"
    if cost < 1000:
        return f"${cost:.0f}"
    return f"${cost:,.0f}"


if __name__ == "__main__":
    # Test pricing lookups
    print("Testing pricing lookups:")
    test_models = ["Opus", "Sonnet", "Haiku", "claude-3-5-sonnet-20241022", "unknown"]
    for model in test_models:
        pricing = get_model_pricing(model)
        print(f"  {model}: {pricing}")

    # Test cost calculation
    print("\nTesting cost calculation:")
    cost = calculate_cost(
        input_tokens=1_000_000,
        output_tokens=500_000,
        cache_creation_tokens=100_000,
        cache_read_tokens=50_000,
        model_name="Sonnet"
    )
    print(f"  1M input + 500K output + 100K cache create + 50K cache read (Sonnet): {format_cost(cost)}")
