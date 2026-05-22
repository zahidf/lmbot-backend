import sys
import pytest
from unittest.mock import MagicMock

# Mock langchain modules before importing the service,
# since langchain_openai has a broken import in this environment.
sys.modules.setdefault("langchain_openai", MagicMock())
sys.modules.setdefault("langchain_core", MagicMock())
sys.modules.setdefault("langchain_core.prompts", MagicMock())
sys.modules.setdefault("langchain_core.output_parsers", MagicMock())

from app.infrastructure.external_services.langchain_llm_service import (
    LangChainLLMService,
)


class TestGasSafetyDisclaimer:
    """Test the deterministic gas safety disclaimer post-processor"""

    @pytest.fixture
    def service(self):
        """Create service instance (LLM/embeddings not needed for disclaimer tests)"""
        return LangChainLLMService(openai_api_key="test-key")

    def test_disclaimer_appended_when_regulated_keywords_present(self, service):
        """Response mentioning regulated work without a disclaimer gets one appended"""
        response = (
            "To commission the TX burner, perform precommissioning checks "
            "on the control panel, fan, and gas system."
        )
        result = service._ensure_safety_disclaimer(response)
        assert result.endswith(service.GAS_SAFETY_DISCLAIMER)
        assert "Gas Safe registered engineer" in result

    def test_disclaimer_not_duplicated_when_already_present(self, service):
        """Response that already contains a disclaimer is returned unchanged"""
        response = (
            "The commissioning procedure involves a dry run of the burner.\n\n"
            "This work must be carried out by a qualified Gas Safe registered engineer."
        )
        result = service._ensure_safety_disclaimer(response)
        assert result == response

    def test_disclaimer_not_added_for_general_queries(self, service):
        """Response about general product info should not get a disclaimer"""
        response = (
            "The TX Series is a range of high-efficiency industrial burners "
            "designed for process heating applications."
        )
        result = service._ensure_safety_disclaimer(response)
        assert result == response
        assert service.GAS_SAFETY_DISCLAIMER not in result

    def test_multiple_keywords_single_disclaimer(self, service):
        """Response with multiple regulated keywords gets only one disclaimer"""
        response = (
            "The gas valve should be checked. Inspect the electrode gap. "
            "Complete commissioning checks on the gas train."
        )
        result = service._ensure_safety_disclaimer(response)
        assert result.count("Gas Safe registered engineer") == 1

    def test_case_insensitive_keyword_matching(self, service):
        """Keywords are detected regardless of case"""
        response = "COMMISSIONING of the Gas Valve must follow the procedure."
        result = service._ensure_safety_disclaimer(response)
        assert "Gas Safe registered engineer" in result

    def test_disclaimer_detected_case_insensitive(self, service):
        """Existing disclaimer is detected regardless of case"""
        response = (
            "Adjust the gas valve settings as described.\n\n"
            "A QUALIFIED ENGINEER must perform this work."
        )
        result = service._ensure_safety_disclaimer(response)
        assert result == response

    def test_gas_supply_keyword_triggers_disclaimer(self, service):
        """The 'gas supply' keyword triggers the disclaimer"""
        response = "Isolate the gas supply at the service cock before work."
        result = service._ensure_safety_disclaimer(response)
        assert "Gas Safe registered engineer" in result

    def test_isolat_keyword_covers_isolate_and_isolating(self, service):
        """The 'isolat' stem matches both 'isolate' and 'isolating'"""
        for word in ["Isolate the gas", "Isolating electrical supplies"]:
            result = service._ensure_safety_disclaimer(word)
            assert "Gas Safe registered engineer" in result

    def test_empty_response_unchanged(self, service):
        """Empty response is returned as-is"""
        result = service._ensure_safety_disclaimer("")
        assert result == ""

    def test_fault_code_response_no_disclaimer(self, service):
        """Fault code explanations without regulated keywords should not get a disclaimer"""
        response = (
            "Fault code E3 indicates a flame failure during operation. "
            "Check the flame detector and wiring connections."
        )
        result = service._ensure_safety_disclaimer(response)
        assert result == response
