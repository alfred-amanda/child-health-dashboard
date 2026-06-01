# Colorblind and WCAG review

Automated token checks are run by `npm run test:a11y`.

Manual review notes:

- Status is encoded by hue + shape + icon + text, so deuteranopia/protanopia users are not dependent on color.
- Calm watercolor palette uses dark text on warm off-white/surface tokens and passes WCAG AA in the automated ratio check.
- Alarm mode deliberately breaks the calm palette with saturated red, yellow status strip, thick borders, uppercase urgent copy, and shape/icon badges.
- Tap targets are set at 48px minimum for 3am/one-handed use.
