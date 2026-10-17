// Pure decisions behind "the new question moves to the top of the transcript".

/** Gap between the scroller's top edge and the question bubble. */
export const QUESTION_TOP_OFFSET_PX = 16;

/** Only scroll when the transcript overflows; a short chat stays where it is. */
export function shouldScrollToQuestion(scrollHeight: number, clientHeight: number): boolean {
  return scrollHeight > clientHeight;
}

/** `scrollTop` that puts the bubble `offsetPx` below the scroller's top.
 * `bubbleOffsetTop` is measured inside the scroller's padding box content (its
 * positioned inner column), so the scroller's own top padding is added back. */
export function scrollTargetFor(bubbleOffsetTop: number, scrollerPaddingTop: number, offsetPx: number = QUESTION_TOP_OFFSET_PX): number {
  return Math.max(0, scrollerPaddingTop + bubbleOffsetTop - offsetPx);
}
