# Search Bar Animation Refinement Guide

## Scope

This guide is for refining the target search bar in:

`C:\Users\Yasindu\Desktop\Stuff\research 2027\dev\frontend`

The target component is `src/features/tutor/SearchComposer.tsx`, with styles in `src/index.css`. The reference behavior is the composer in `C:\Users\Yasindu\Desktop\Chat_Research\IT22638168\dev\frontend\app\app\chat.tsx`.

Although it is called a search bar, it is technically a multiline message composer. The search icon is the submit button. There is no autocomplete or search-result dropdown in the reference behavior.

## Target interaction model

The component must follow this sequence:

```text
Keyboard input
    ↓
Update controlled draft state
    ↓
Estimate wrapped lines from text and width
    ↓
Measure real textarea scrollHeight
    ↓
Stay single-line until the idle layout truly wraps
    ↓
Switch to dynamic multiline mode
    ↓
Grow in discrete line steps
    ↓
Reduce font size at approximately four lines
    ↓
Stop growing at six lines
    ↓
Enable internal scrolling
    ↓
Submit through the circular search/send button
```

The target already contains most of this logic. Refinement should concentrate on animation timing, stable mode switching, discrete height growth, and consistent button spacing.

## State responsibilities

| State | Purpose |
|---|---|
| `draft` | Current characters entered by the keyboard |
| `focused` | Whether the field or topic control is engaged |
| `composerW` | Actual composer width used for line estimation |
| `autoH` | Measured textarea content height |
| `dynamicMode` | Single-line versus multiline layout mode |
| `topicPickerOpen` | Whether the topic picker is visible |
| `idle` | Whether no messages have been submitted |
| `sendDisabled` | Whether submission is unavailable |

## Capturing keyboard characters

The textarea must remain controlled:

```tsx
const [draft, setDraft] = useState('');

<textarea
  value={draft}
  onChange={(event) => {
    setFocused(true);
    onEngage();
    setDraft(event.currentTarget.value);
  }}
/>
```

Every character, deletion, paste, and replacement updates `draft`. Each update recalculates the input mode, height, line count, font size, and scrolling state.

Do not make the textarea uncontrolled. The draft is needed for sending and for restoring a failed message.

## Single-line mode

The reference begins with a compact single-line input:

```tsx
const MAX_LINES = 6;
const singleLineBox = 40;
const lineHeight = 22;
const maxHeight = MAX_LINES * lineHeight + 14;
```

In single-line mode:

- The textarea height is `40px`.
- The line height is also `40px`, which vertically centers the text.
- The input reserves `52px` on the right for the send button.
- The composer remains compact until the text actually wraps.

The target currently uses `const singleLine = !dynamicMode`. Preserve that behavior, but make sure the mode is reset when text becomes short again or after submission.

## Detecting the multiline transition

The component measures the actual browser `<textarea>` through `textareaRef`. To test the idle layout, it temporarily applies the reserved button space and single-line line height:

```tsx
textarea.style.paddingRight = '52px';
textarea.style.lineHeight = `${singleLineBox}px`;
textarea.style.height = '0px';
const idleHeight = textarea.scrollHeight;
```

Dynamic mode begins when:

```tsx
const wrapsIdle =
  draft.includes('\n') ||
  idleHeight > singleLineBox + 14;
```

The `14px` tolerance is important. It prevents the component from flickering between modes at the wrapping boundary.

When dynamic mode begins:

- Set `dynamicMode` to `true`.
- Use `22px` line height.
- Change right padding from `52px` to `14px`.
- Add approximately `52px` bottom padding to the composer.
- Keep the send button at the lower-right.

When text becomes short enough to fit again, reset `dynamicMode` and `autoH` so stale measured height cannot keep the composer expanded.

## Real height measurement

The target uses `scrollHeight` rather than only character counting:

```tsx
textarea.rows = 1;
textarea.style.height = '0px';
const measured = textarea.scrollHeight;
```

The measured value should be converted into discrete line states:

```tsx
const steppedHeight = Math.max(
  lineHeight,
  Math.round(measured / lineHeight) * lineHeight
);
```

This prevents fractional browser measurements from causing continuous micro-resizing while a line is being filled. The visible sequence should be:

```text
one line → two lines → three lines → four lines → five lines → six lines
```

Do not use a continuously changing height if the goal is to match the reference animation.

## Height and line cap

The line count should be calculated as:

```tsx
const rawLines = autoH
  ? Math.max(1, Math.round(autoH / lineHeight))
  : estimatedLines;

const lineCount = Math.min(
  MAX_LINES,
  Math.max(1, singleLine ? 1 : rawLines)
);

const textHeight = singleLine
  ? singleLineBox
  : Math.min(
      maxHeight,
      Math.max(autoH, lineCount * lineHeight) + 8
    );

const atCap = !singleLine && rawLines >= MAX_LINES;
```

Expected values:

- Idle height: `40px`.
- Multiline line height: `22px`.
- Maximum visible lines: `6`.
- Maximum calculated height: approximately `146px`.
- Internal scrolling starts at the six-line cap.

Apply scrolling only at the cap:

```tsx
overflowY: atCap ? 'auto' : 'hidden'
```

## Width-based estimate

The target uses `ResizeObserver` to update `composerW`. The estimate should remain monotonic so font-size changes do not cause an oscillation:

```tsx
const estimatedLines = draft.split('\n').reduce(
  (count, line) => count + Math.max(
    1,
    Math.ceil(
      line.length /
      Math.max(6, Math.floor((composerW - 24) / 11))
    )
  ),
  0
);
```

This is an estimate only. `scrollHeight` remains the source of truth for actual wrapped height.

## Font-size transition

The font becomes compact around four estimated lines:

```tsx
const compact = dynamicMode && estimatedLines >= 4;
```

The compact value is `15px`. Keep the decision based on the monotonic estimate rather than measured lines, because a smaller font can reflow the text and otherwise cause the state to switch back and forth.

The CSS transition should remain narrow:

```css
.tutor-composer textarea {
  transition: height 180ms ease, font-size 180ms ease;
}
```

Do not use `transition: all`, because padding and overflow changes should not animate unpredictably.

## Composer position animation

The base composer uses a `230px` raised offset when the conversation is empty and the input is unfocused:

```tsx
const raised = idle && !focused;

<div className={`tutor-composer px-4 ${raised ? 'tutor-composer-idle' : ''}`}>
```

The target CSS should keep:

```css
.tutor-composer {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  transition: transform 240ms ease;
}

.tutor-composer-idle {
  transform: translateY(-230px);
}
```

Required behavior:

- Empty and unfocused: raised by `230px`.
- Focused or after the first message: returns to the bottom.
- Both directions animate over `240ms`.
- Use `transform`, not `top`, `bottom`, margin, or layout height animation.

## Empty-state fade animation

The target already matches the reference timing:

```css
.tutor-empty-state {
  opacity: 1;
  transition: opacity 160ms ease;
}

.tutor-empty-state-hidden {
  opacity: 0;
  pointer-events: none;
}
```

The hidden class must be applied when the user:

- Focuses the textarea.
- Types a character.
- Opens the topic picker.

`pointer-events: none` is required so invisible empty-state content cannot block the composer.

## Send-button geometry

The send button should remain a `44px` circular control:

```css
.tutor-send-button {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 44px;
  min-width: 44px;
  height: 44px;
  border-radius: 999px;
}
```

Use these padding rules:

```text
Single-line: 0 52px 0 58px
Multiline:   0 14px 0 58px
```

Multiline mode must add `52px` bottom padding to the composer so the final text line never passes behind the send button.

## Topic picker behavior

The target adds a topic-picker button that the reference composer does not have. Opening it must still engage the composer:

```tsx
onClick={() => {
  setFocused(true);
  onEngage();
  setTopicPickerOpen((value) => !value);
}}
```

The picker should appear above the composer and must not change the textarea's measured width or height calculation.

## Submission reset

After a successful submit attempt, reset all layout state immediately:

```tsx
setDraft('');
setAutoH(0);
setDynamicMode(false);
void onSend(text);
```

This returns the component to the compact single-line geometry. Do not reset only `draft`; stale `autoH` or `dynamicMode` can leave the next message in multiline mode.

## Target-specific cleanup

The target CSS contains this selector:

```css
.tutor-composer textarea.tutor-composer-input-multiline { ... }
```

The current JSX does not add that class. Padding is currently controlled inline, so the selector is unused and potentially confusing. Choose one approach:

1. Remove the unused selector and keep inline padding as the source of truth; or
2. Add the class when `dynamicMode` is true and move the padding rule fully into CSS.

Do not maintain two competing sources of truth for multiline padding.

The existing scrollbar rules should remain for cross-browser behavior:

```css
scrollbar-width: none;

.tutor-composer textarea::-webkit-scrollbar {
  display: none;
}
```

## Visual acceptance checklist

- [ ] Empty composer is approximately `230px` above the docked position.
- [ ] Docking and undocking take `240ms`.
- [ ] Empty content fades in or out over `160ms`.
- [ ] Single-line mode remains stable until actual idle wrapping.
- [ ] The first wrapped line appears without flicker.
- [ ] Height grows in discrete `22px` line steps.
- [ ] Font size becomes `15px` around four lines.
- [ ] Font-size state does not oscillate.
- [ ] Six lines are visible before scrolling begins.
- [ ] The send button never overlaps text.
- [ ] Deleting text returns the composer to one line.
- [ ] Sending resets height and mode.
- [ ] Typing and opening the topic picker both hide the empty state.
- [ ] Narrow and wide viewport widths produce the same state transitions.
- [ ] Disabled state preserves the composer geometry.

## Recommended refinement order

1. Verify controlled keyboard input and submit reset.
2. Verify the `230px` transform and `240ms` transition.
3. Verify the `160ms` empty-state fade.
4. Verify idle-wrap detection with the `52px` button reservation.
5. Verify discrete `22px` height stepping.
6. Verify compact text at four lines.
7. Verify the six-line cap and internal scrolling.
8. Verify button padding and lower-right positioning.
9. Test deleting from six lines back to one line.
10. Test the topic picker and disabled state.
