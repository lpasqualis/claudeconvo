# Homebrew Tap Setup Instructions

To make claudeconvo available via Homebrew, you'll need to create a separate tap repository.

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
   cp /path/to/claudeconvo/Formula/claudeconvo.rb Formula/claudeconvo.rb
   ```

4. **After releasing a version**, update the formula:
   - Replace the `url` with the actual release tarball URL
   - Calculate the SHA256: `curl -L https://github.com/lpasqualis/claudeconvo/archive/refs/tags/v0.1.0.tar.gz | shasum -a 256`
   - Update the `sha256` field in the formula

5. **Commit and push** the formula:
   ```bash
   git add Formula/claudeconvo.rb
   git commit -m "Add claudeconvo formula"
   git push
   ```

## Users Can Then Install Via:

```bash
brew tap lpasqualis/tap
brew install claudeconvo
```

Or in a single command:
```bash
brew install lpasqualis/tap/claudeconvo
```

## Updating the Formula

When you release new versions:

1. Update the `url` and `sha256` in the formula
2. Commit and push to your tap repository
3. Users can update with: `brew upgrade claudeconvo`

## Alternative: Homebrew Core

For wider distribution, you can later submit to homebrew-core, but this requires:
- Significant user base
- Stable releases
- Meeting Homebrew's acceptance criteria