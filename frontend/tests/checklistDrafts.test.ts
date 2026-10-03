import { describe, expect, test } from "bun:test";
import { acknowledgeSavedDraft, checkboxResult, refreshCleanDrafts } from "../src/composables/checklistDrafts";

describe("checklist item drafts", () => {
    test("checkbox preserves arbitrary results and explicitly clears to pending", () => {
        expect(checkboxResult("Mesure 42", true)).toBe("Mesure 42");
        expect(checkboxResult(null, true)).toBe("OK");
        expect(checkboxResult("Mesure 42", false)).toBeNull();
        expect(checkboxResult("", true)).toBe("");
    });

    test("refresh updates clean items but preserves dirty input, including explicit null", () => {
        const drafts = {
            1: { result: null, comment: "" },
            2: { result: "OK", comment: "ancien" },
        };
        refreshCleanDrafts(drafts, new Set([1]), [
            { id: 1, result: "Mesure 42", comment: "serveur" },
            { id: 2, result: null, comment: "nouveau" },
        ]);
        expect(drafts[1]).toEqual({ result: null, comment: "" });
        expect(drafts[2]).toEqual({ result: null, comment: "nouveau" });
    });

    test("partial save acknowledges only successful items and preserves failures after refresh", () => {
        const drafts = {
            1: { result: "Mesure 42", comment: "commentaire modifié" },
            2: { result: null, comment: "échec à retenter" },
        };
        const dirty = new Set([1, 2]);
        acknowledgeSavedDraft(drafts, dirty, 1, { ...drafts[1] }, { ...drafts[1] });
        refreshCleanDrafts(drafts, dirty, [
            { id: 1, ...drafts[1] },
            { id: 2, result: "OK", comment: "ancien" },
        ]);
        expect([...dirty]).toEqual([2]);
        expect(drafts[1].result).toBe("Mesure 42");
        expect(drafts[2]).toEqual({ result: null, comment: "échec à retenter" });
    });

    test("input edited while PATCH is pending remains dirty even after successful response", () => {
        const submitted = { result: "OK", comment: "envoyé" };
        const drafts = { 1: { result: null, comment: "saisie pendant sauvegarde" } };
        const dirty = new Set([1]);
        acknowledgeSavedDraft(drafts, dirty, 1, submitted, submitted);
        refreshCleanDrafts(drafts, dirty, [{ id: 1, ...submitted }]);
        expect(dirty.has(1)).toBe(true);
        expect(drafts[1]).toEqual({ result: null, comment: "saisie pendant sauvegarde" });
    });
});
