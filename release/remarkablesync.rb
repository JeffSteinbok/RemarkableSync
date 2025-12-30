class Remarkablesync < Formula
  desc "Backup and convert reMarkable tablet notebooks to PDF"
  homepage "https://github.com/JeffSteinbok/RemarkableSync"
  url "https://github.com/JeffSteinbok/RemarkableSync/archive/refs/tags/v1.0.2.tar.gz"
  sha256 "" # Will be calculated after creating the release
  license "MIT"

  depends_on "python@3.11"
  depends_on "cairo"
  depends_on "pkg-config"

  def install
    # Create a virtualenv
    virtualenv_install_with_resources
  end

  test do
    # Test that the command runs and shows help
    assert_match "RemarkableSync", shell_output("#{bin}/RemarkableSync --help")
  end
end
