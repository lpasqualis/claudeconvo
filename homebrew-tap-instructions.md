# Homebrew Tap Setup Instructions

To make claudelog available via Homebrew, you'll need to create a separate tap repository.

## Steps to Create Your Homebrew Tap

1. **Create a new repository** named `homebrew-tap` on GitHub:
   ```
   https://github.com/lpasqualis/homebrew-tap
   ```

2. **Clone the repository locally**:
   ```bash
   git clone https://github.com/lpasqualis/homebrew-tap.git
   cd homebrew-tap
   ```

3. **Copy the formula** from this project:
   ```bash
   cp /path/to/claudelog/Formula/claudelog.rb Formula/claudelog.rb
   ```

4. **After releasing a version**, update the formula:
   - Replace the `url` with the actual release tarball URL
   - Calculate the SHA256: `curl -L https://github.com/lpasqualis/claudelog/archive/refs/tags/v0.1.0.tar.gz | shasum -a 256`
   - Update the `sha256` field in the formula

5. **Commit and push** the formula:
   ```bash
   git add Formula/claudelog.rb
   git commit -m "Add claudelog formula"
   git push
   ```

## Users Can Then Install Via:

```bash
brew tap lpasqualis/tap
brew install claudelog
```

Or in a single command:
```bash
brew install lpasqualis/tap/claudelog
```

## Updating the Formula

When you release new versions:

1. Update the `url` and `sha256` in the formula
2. Commit and push to your tap repository
3. Users can update with: `brew upgrade claudelog`

## Alternative: Homebrew Core

For wider distribution, you can later submit to homebrew-core, but this requires:
- Significant user base
- Stable releases
- Meeting Homebrew's acceptance criteria