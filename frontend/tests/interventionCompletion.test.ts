import { describe, expect, test } from "bun:test";
import { checklistReady, completionPayload, interventionResultLabel, interventionResultOptions, isInterventionResult } from "../src/composables/interventionCompletion";
import type { ChecklistItemRef, InterventionHistoryItem } from "../src/api/client";

describe("global intervention completion", () => {
    test("requires an explicit exact six-value result", () => {
        expect(interventionResultOptions.map(option => option.value)).toEqual([
            "RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED", "PART_NEEDED", "QUOTE_NEEDED", "RESCHEDULE",
        ]);
        for (const option of interventionResultOptions) {
            expect(isInterventionResult(option.value)).toBe(true);
            expect(option.label.length).toBeGreaterThan(0);
        }
        for (const invalid of [null, undefined, "", "resolved", "COMPLETED", "OK", "FAILED"]) {
            expect(isInterventionResult(invalid)).toBe(false);
            expect(() => completionPayload(invalid, "", false)).toThrow();
        }
    });
    test("omits untouched observations and sends explicit edits", () => {
        expect(completionPayload("PART_NEEDED", "Old note", false)).toEqual({ result: "PART_NEEDED" });
        expect(completionPayload("QUOTE_NEEDED", "New note", true)).toEqual({ result: "QUOTE_NEEDED", observations: "New note" });
        expect(completionPayload("RESCHEDULE", "", true)).toEqual({ result: "RESCHEDULE", observations: "" });
    });
    test("checklist item results remain free text, not global outcomes", () => {
        const freeText: Pick<ChecklistItemRef, "result"> = { result: "Pressure: 2 bar" };
        expect(checklistReady([freeText, { result: "FAILED" }, { result: "OK" }])).toBe(true);
        expect(isInterventionResult(freeText.result)).toBe(false);
        expect(checklistReady([{ result: null }, { result: "RESOLVED" }])).toBe(false);
        expect(checklistReady([])).toBe(true);
    });
    test("historical null is unknown; completed does not mean resolved", () => {
        const history: InterventionHistoryItem = { id: 1, title: "Legacy", status: "COMPLETED",
            result: null, completed_at: null, technician_name: null };
        expect(history.status).toBe("COMPLETED");
        expect(interventionResultLabel(history.result)).toBe("Non renseigné");
        history.result = "PART_NEEDED";
        expect(history.status).toBe("COMPLETED");
        expect(interventionResultLabel(history.result)).toBe("Pièce nécessaire");
    });
});
