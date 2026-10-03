import { describe, expect, test } from "bun:test";
import { groupPhotos, photoUsages, materialRow, reconcileMaterials, validateMaterial } from "../src/utils/interventionMedia";
import type { MaterialItem, PhotoResponse } from "../src/api/client";

const item: MaterialItem = { id: 1, intervention_id: 2, designation: "Tube", quantity: null, unit: null, position: 0 };
const valid = { designation: "Tube", quantity: "1.234", unit: "mètre linéaire" };

describe("material validation", () => {
    test("accepts numeric quantities and free units; outputs a JSON number", () => {
        expect(validateMaterial(valid).data).toEqual({ designation: "Tube", quantity: 1.234, unit: "mètre linéaire" });
        expect(validateMaterial({ ...valid, quantity: 999999999.999 }).data?.quantity).toBe(999999999.999);
    });
    test("rejects missing, nonpositive, excessive and overprecise quantities", () => {
        for (const quantity of [null, "", 0, -1, "1.2345", "NaN", Infinity, 1000000000, "1e3"])
            expect(validateMaterial({ ...valid, quantity }).error).toBeTruthy();
    });
    test("requires bounded designation and unit", () => {
        for (const designation of [" ", "x".repeat(256)])
            expect(validateMaterial({ ...valid, designation }).error).toBeTruthy();
        for (const unit of [null, " ", "x".repeat(51)])
            expect(validateMaterial({ ...valid, unit }).error).toBeTruthy();
    });
});

describe("draft reconciliation", () => {
    test("keeps historic nulls and refreshes only clean rows", () => {
        expect(materialRow(item).quantity).toBeNull();
        expect(materialRow(item).unit).toBeNull();
        const dirty = { ...materialRow(item), designation: "Brouillon", dirty: true };
        const added = { ...materialRow(item), id: -1, dirty: true };
        expect(reconcileMaterials([dirty, added], [item])).toEqual([dirty, added]);
        expect(reconcileMaterials([materialRow(item)], [{ ...item, designation: "Actualisé" }])[0].designation).toBe("Actualisé");
    });
    test("preserves saving rows and drafts missing from a refresh", () => {
        const saving = { ...materialRow(item), saving: true };
        expect(reconcileMaterials([saving], [item])[0]).toBe(saving);
        expect(reconcileMaterials([saving], [])).toEqual([saving]);
    });
});

test("six localized photo groups, without routing other usages to AFTER", () => {
    const photos: PhotoResponse[] = photoUsages.map((usage, id) => ({
        id, usage: usage.value, file_url: "/photo", thumbnail_url: null, taken_at: "2026-01-01",
    }));
    const groups = groupPhotos(photos);
    expect(groups.map((group) => group.label)).toEqual(["Avant", "Après", "Équipement", "Anomalie", "Pièce", "Autre"]);
    expect(groups.every((group) => group.photos.length === 1 && group.photos[0].usage === group.value)).toBe(true);
    expect(groupPhotos([]).every((group) => group.photos.length === 0)).toBe(true);
});
