/**
 * Attempts to parse a structured legal response JSON from the assistant's content string.
 * Returns the parsed object if valid, or null if the content is plain text / old format.
 */
export function parseStructuredResponse(content) {
  if (!content || typeof content !== 'string') return null;

  const trimmed = content.trim();

  // Quick heuristic: must look like a JSON object
  if (!trimmed.startsWith('{')) return null;

  try {
    // Handle possible markdown code fences wrapping JSON
    let jsonStr = trimmed;
    if (jsonStr.startsWith('```')) {
      jsonStr = jsonStr.replace(/^```(?:json)?\s*\n?/, '').replace(/\n?```\s*$/, '');
    }

    const parsed = JSON.parse(jsonStr);

    // Validate required fields
    if (
      parsed &&
      typeof parsed === 'object' &&
      typeof parsed.mainAnswer === 'string' &&
      parsed.mainAnswer.trim().length > 0
    ) {
      return {
        legalDomain: parsed.legalDomain || null,
        mainAnswer: parsed.mainAnswer,
        legalBasis: parsed.legalBasis || null,
        recommendedNextSteps: Array.isArray(parsed.recommendedNextSteps)
          ? parsed.recommendedNextSteps.filter((s) => typeof s === 'string' && s.trim())
          : [],
      };
    }
  } catch {
    // Not valid JSON — fall through to null
  }

  return null;
}
