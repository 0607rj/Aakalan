"""Items the client provides (hosting, web address, SSL), found in the document's own text."""

from app.services.extraction.client_provided import find_client_provided, sentences
from app.services.quick.config import quick_config

PDF_BULLET = ""  # a bullet from a PDF symbol font


def found(*pages: str) -> dict[str, tuple[str, str, int]]:
    rules = quick_config().client_provided
    assert rules is not None
    out = find_client_provided(rules, list(enumerate(pages, start=1)), "rfp.pdf")
    return {k: (value, ev.quote, ev.page) for k, (value, ev) in out.items()}


def test_department_provides_domain_and_hosting() -> None:
    """The PBD tender's sentence (p.17), after a PDF symbol-font bullet."""
    page = (
        f"Scope of work\n{PDF_BULLET} Domain and hosting will be provided to the agency from the"
        f"\ndepartment.\n{PDF_BULLET} The agency shall design the portal."
    )
    out = found("Introduction.", page)
    quote = "Domain and hosting will be provided to the agency from the department."
    assert out == {"hosting": ("existing", quote, 2), "web_domain": ("client", quote, 2)}


def test_vendor_provides_is_not_client_provided() -> None:
    assert found("Hosting shall be provided by the bidder as per the department's policy.") == {}
    assert found("The bidder shall provide the SSL certificate for the department portal.") == {}


def test_no_client_word_no_answer() -> None:
    assert found("Hosting will be provided on a government cloud.") == {}


def test_ssl_from_the_client() -> None:
    out = found("The SSL certificate shall be provided by the client.")
    assert out == {
        "ssl_certificate": ("client", "The SSL certificate shall be provided by the client.", 1)
    }


def test_sentences_split_on_bullets_and_numbers() -> None:
    text = f"{PDF_BULLET} First item.\n{PDF_BULLET} Second item\n1. Third\na) Fourth; fifth"
    assert sentences(text) == ["First item.", "Second item", "Third", "Fourth;", "fifth"]
