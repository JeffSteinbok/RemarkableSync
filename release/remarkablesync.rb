class Remarkablesync < Formula
  desc "Backup and convert reMarkable tablet notebooks to PDF"
  homepage "https://github.com/JeffSteinbok/RemarkableSync"
  url "https://github.com/JeffSteinbok/RemarkableSync/archive/refs/tags/v1.0.3.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"
  head "https://github.com/JeffSteinbok/RemarkableSync.git", branch: "main"

  depends_on "python@3.13"
  depends_on "cairo"       # Required for reportlab PDF generation
  depends_on "pkg-config"  # Required for building some Python packages

  def install
    # Create a virtualenv and install the package with all dependencies
    virtualenv_create(libexec, "python3.13")
    system libexec/"bin/pip", "install", "-v", "--no-binary", ":all:",
           "--ignore-installed", buildpath

    # Create wrapper script in bin
    (bin/"RemarkableSync").write_env_script libexec/"bin/RemarkableSync",
                                             PATH: "#{libexec}/bin:$PATH"
  end

  test do
    # Test that the command runs and shows help
    assert_match "RemarkableSync", shell_output("#{bin}/RemarkableSync --help")

    # Test that rmc is available in the virtualenv
    system libexec/"bin/pip", "show", "rmc"
  end
end
