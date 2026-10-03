import type { InterventionCompletionPayload, InterventionResult } from "../api/client";

export const interventionResultOptions: { value: InterventionResult; label: string }[] = [
    { value: "RESOLVED", label: "Résolu" },
    { value: "PARTIALLY_RESOLVED", label: "Partiellement résolu" },
    { value: "UNRESOLVED", label: "Non résolu" },
    { value: "PART_NEEDED", label: "Pièce nécessaire" },
    { value: "QUOTE_NEEDED", label: "Devis nécessaire" },
    { value: "RESCHEDULE", label: "À replanifier" },
];

export function isInterventionResult(value: unknown): value is InterventionResult {
    return interventionResultOptions.some(option => option.value === value);
}

export function interventionResultLabel(value: InterventionResult | null | undefined): string {
    return interventionResultOptions.find(option => option.value === value)?.label ?? "Non renseigné";
}

export function checklistReady(items: readonly { result: string | null }[]): boolean {
    return items.every(item => item.result !== null);
}

export function completionPayload(result: unknown, observations: string, observationsEdited: boolean): InterventionCompletionPayload {
    if (!isInterventionResult(result)) throw new Error("Choisissez un résultat global.");
    // Omission preserves existing observations; an explicitly empty edit remains an edit.
    return observationsEdited ? { result, observations } : { result };
}
