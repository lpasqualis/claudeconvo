class Claudeconvo < Formula
  include Language::Python::Virtualenv

  desc "Display Claude Code session history as colored conversations"
  homepage "https://github.com/lpasqualis/claudeconvo"
  url "https://github.com/lpasqualis/claudeconvo/archive/refs/tags/v0.1.0.tar.gz"
  sha256 ""  # This will need to be updated after the release is created
  license "MIT"
  head "https://github.com/lpasqualis/claudeconvo.git", branch: "main"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    # Test that the command runs and shows help
    assert_match "usage:", shell_output("#{bin}/claudeconvo --help")
    
    # Test version output (once implemented)
    # assert_match version.to_s, shell_output("#{bin}/claudeconvo --version")
  end
end