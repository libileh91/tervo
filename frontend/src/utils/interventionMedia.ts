import type { MaterialInput, MaterialItem, PhotoResponse, PhotoUsage } from "../api/client";

export const photoUsages: { value: PhotoUsage; label: string }[] = [
    { value: "BEFORE", label: "Avant" },
    { value: "AFTER", label: "Après" },
    { value: "EQUIPMENT", label: "Équipement" },
    { value: "ANOMALY", label: "Anomalie" },
    { value: "PART", label: "Pièce" },
    { value: "OTHER", label: "Autre" },
];

export function groupPhotos(photos: PhotoResponse[]) {
    return photoUsages.map((usage) => ({
        ...usage,
        photos: photos.filter((photo) => photo.usage === usage.value),
    }));
}

export interface MaterialRow {
    id: number;
    designation: string;
    quantity: string | number | null;
    unit: string | null;
    dirty: boolean;
    saving: boolean;
    error: string | null;
}

export function materialRow(item: MaterialItem): MaterialRow {
    return { id: item.id, designation: item.designation, quantity: item.quantity, unit: item.unit,
        dirty: false, saving: false, error: null };
}

/** Refresh clean server rows, keeping both partial edits and new unsaved rows. */
export function reconcileMaterials(rows: MaterialRow[], items: MaterialItem[]): MaterialRow[] {
    const byId = new Map(rows.map((row) => [row.id, row]));
    const refreshed = items.map((item) => {
        const draft = byId.get(item.id);
        return draft && (draft.dirty || draft.saving) ? draft : materialRow(item);
    });
    return [...refreshed, ...rows.filter((row) =>
        row.id < 0 || ((row.dirty || row.saving) && !items.some((item) => item.id === row.id)))];
}

export function validateMaterial(row: Pick<MaterialRow, "designation" | "quantity" | "unit">):
    { data: MaterialInput; error?: never } | { error: string; data?: never } {
    const designation = row.designation.trim();
    const unit = row.unit?.trim() ?? "";
    if (!designation || designation.length > 255) return { error: "La désignation est obligatoire (255 caractères maximum)." };
    const text = String(row.quantity ?? "").trim();
    const quantity = Number(text);
    if (!/^\d+(?:\.\d{1,3})?$/.test(text) || !Number.isFinite(quantity) || quantity <= 0 || quantity > 999999999.999)
        return { error: "Quantité obligatoire, positive, au plus 999999999.999 et trois décimales." };
    if (!unit || unit.length > 50) return { error: "L’unité est obligatoire (50 caractères maximum)." };
    return { data: { designation, quantity, unit } };
}
