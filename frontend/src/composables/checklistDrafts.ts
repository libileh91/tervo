export type ChecklistDraft = { result: string | null; comment: string | null };
export type ItemDraft = ChecklistDraft & { id: number };

export function checkboxResult(current: string | null, checked: boolean): string | null {
    return checked ? current ?? "OK" : null;
}

export function refreshCleanDrafts(
    drafts: Record<number, ChecklistDraft>,
    dirty: Set<number>,
    items: ItemDraft[],
) {
    for (const item of items) {
        if (!dirty.has(item.id)) drafts[item.id] = { result: item.result, comment: item.comment };
    }
}

// A successful response acknowledges the submitted values, not any newer user input.
export function acknowledgeSavedDraft(
    drafts: Record<number, ChecklistDraft>,
    dirty: Set<number>,
    id: number,
    submitted: ChecklistDraft,
    saved: ChecklistDraft,
) {
    const current = drafts[id];
    if (current.result === submitted.result && current.comment === submitted.comment) {
        dirty.delete(id);
        drafts[id] = { result: saved.result, comment: saved.comment };
    }
}
