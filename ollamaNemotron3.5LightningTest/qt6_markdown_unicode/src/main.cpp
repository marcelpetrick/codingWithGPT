#include <QApplication>
#include <QMainWindow>
#include <QTextEdit>
#include <QLabel>
#include <QSplitter>
#include <QStatusBar>
#include <QMessageBox>
#include <QFontDatabase>
#include <QFile>
#include <QTextStream>
#include <QRegularExpression>
#include <QMap>
#include <QDateTime>

/// Simple markdown-to-unicode converter for common formatting elements.
/**
 Converts markdown syntax to unicode characters that provide visual enhancement.
 Uses widely-supported unicode characters to ensure correct rendering across fonts.
 Processes text line by line with prioritized transformations.
 */
class MarkdownToUnicodeConverter {
public:
    /// Convert a full markdown document to unicode-enhanced text.
    static QString convert(const QString &markdown) {
        if (markdown.isEmpty()) {
            return QString();
        }

        // Split into lines preserving empty lines (unlike Qt::SkipEmptyParts)
        QStringList lines = markdown.split('\n');
        QStringList resultLines;

        for (const QString &line : lines) {
            resultLines.append(convertLine(line));
        }

        return resultLines.join("\n");
    }

    /// Convert a single line of markdown to unicode-enhanced text.
    static QString convertLine(const QString &line) {
        QString result = line;

        // Skip empty lines - pass through unchanged
        if (result.trimmed().isEmpty()) {
            return result;
        }

        // 1. Horizontal rules: --- or *** on their own
        if (result.trimmed() == "---" || result.trimmed() == "***" ||
            result.trimmed() == "___") {
            return QString(qMax(result.size(), 40), QChar(0x2501));
        }

        // 2. Code fences: ``` or ~~~
        result = convertCodeFence(result);

        // 3. Headings: # ## ### #### ##### ######
        result = convertHeading(result);

        // 4. Combined bold+italic ***text*** (MUST come before individual bold/italic)
        result = convertBoldItalic(result);

        // 5. Bold **text** or __text__
        result = convertBold(result);

        // 6. Italic *text* or _text_
        result = convertItalic(result);

        // 7. Strikethrough ~~text~~
        result = convertStrikethrough(result);

        // 8. Lists: lines starting with * or - followed by space
        if ((result.startsWith('*') || result.startsWith('-')) &&
            result.size() > 1 && result.at(1).isSpace()) {
            result = convertListItem(result);
        }

        // 9. Numbered lists: lines starting with digits followed by . and space
        if (QRegularExpression("^[0-9]+\\.\\s").match(result).hasMatch()) {
            result = convertNumberedListItem(result);
        }

        // 10. Blockquotes: lines starting with >
        if (result.startsWith('>')) {
            result = convertBlockquote(result);
        }

        // 11. Inline code `text`
        result = convertInlineCode(result);

        return result;
    }

private:
    /// Convert headings (# through ######) to unicode-framed headers.
    static QString convertHeading(QString line) {
        QRegularExpression re("^(#{1,6})\\s+(.*)");
        QRegularExpressionMatch match = re.match(line);

        if (match.hasMatch()) {
            int level = match.captured(1).size();
            QString text = match.captured(2);

            if (level > 6) level = 6;

            switch (level) {
                case 1: {
                    int width = qMax(text.size() + 4, 20);
                    QString topLine = QChar(0x250C) + QString(width, QChar(0x2500)) + QChar(0x2510);
                    QString bottomLine = QChar(0x2514) + QString(width, QChar(0x2500)) + QChar(0x2518);
                    QString middleLine = QString(QChar(0x2502)) + " " + text + " " + QChar(0x2502);
                    return topLine + "\n" + middleLine + "\n" + bottomLine;
                }
                case 2: {
                    int width = qMax(text.size() + 4, 16);
                    QString borderLine = QString(width, QChar(0x2550));
                    QString middle =
                        QChar(0x2554) + borderLine + QChar(0x2557) + "\n"
                        + QChar(0x2551) + " " + text + " " + QChar(0x2551) + "\n"
                        + QChar(0x255A) + borderLine + QChar(0x255D);
                    return middle;
                }
                case 3:
                    return QString(QChar(0x25A0)) + " " + text + " " + QChar(0x25A0);
                case 4:
                    return QString(QChar(0x25AA)) + " " + text + " " + QChar(0x25AB);
                case 5:
                    return QString(QChar(0x203A)) + " " + text + " " + QChar(0x2039);
                case 6:
                    if (!text.isEmpty()) {
                        return text.left(1).toUpper() + text.mid(1);
                    }
                    return text;
            }
        }

        return line;
    }

    /// Convert code fences (``` or ~~~) to unicode-framed blocks.
    static QString convertCodeFence(QString result) {
        // Opening fence: ```text or ~~~
        if (result.trimmed().startsWith("```") || result.trimmed().startsWith("~~~")) {
            QString lang = result.trimmed().mid(3);
            QString label = lang.isEmpty() ? "code" : lang;
            QString topLine = QChar(0x250C) + QString(qMax(label.size() + 4, 10), QChar(0x2500)) + QChar(0x2510);
            QString bottomLine = QChar(0x2514) + QString(qMax(label.size() + 4, 10), QChar(0x2500)) + QChar(0x2518);
            QString middleLine = QString(QChar(0x2502)) + " " + label + " " + QChar(0x2502);
            return topLine + "\n" + middleLine + "\n" + bottomLine;
        }

        // Closing fence: ``` or ~~~
        if (result.trimmed() == "```" || result.trimmed() == "~~~") {
            QString line = QString(qMax(result.size(), 10), QChar(0x2501));
            return QString(QChar(0x250C)) + line + QChar(0x2510);
        }

        return result;
    }

    /// Convert ***bold+italic*** to unicode combined emphasis.
    /// This MUST be processed before individual bold/italic to avoid
    /// greedy matching of the last ** in *** leaving a stray *.
    static QString convertBoldItalic(QString result) {
        int pos = 0;
        while ((pos = result.indexOf("***", pos)) != -1) {
            int endPos = result.indexOf("***", pos + 3);
            if (endPos != -1) {
                QString inner = result.mid(pos + 3, endPos - pos - 3);
                // Replace ***text*** with combined unicode emphasis
                QString emphasized = QString(QChar(0x25C8)) + QString(QChar(0x2039))
                                     + inner
                                     + QString(QChar(0x00BB)) + QString(QChar(0x25C9));
                result.replace(pos, endPos - pos + 3, emphasized);
                pos += emphasized.size();
            } else {
                break;
            }
        }
        return result;
    }

    /// Convert **bold** or __double underscore__ to unicode bracketed emphasis.
    /// Uses ◈ and ◉ (U+25C8/U+25C9) which are widely supported in most fonts.
    static QString convertBold(QString result) {
        int pos = 0;
        while ((pos = result.indexOf("**", pos)) != -1) {
            int endPos = result.indexOf("**", pos + 2);
            if (endPos != -1) {
                QString inner = result.mid(pos + 2, endPos - pos - 2);
                // Replace **text** with unicode emphasis brackets
                QString emphasized = QString(QChar(0x25C8)) + inner + QString(QChar(0x25C9));
                result.replace(pos, endPos - pos + 2, emphasized);
                pos += emphasized.size();
            } else {
                break;
            }
        }
        return result;
    }

    /// Convert *italic* or _italic_ to unicode italic markers.
    /// Uses ‹ and › (U+2039/U+00BB) which are widely supported.
    static QString convertItalic(QString result) {
        // Handle single asterisks that remain after bold processing.
        // Strategy: find * that is NOT part of ** (double asterisk)
        int pos = 0;
        while ((pos = result.indexOf('*', pos)) != -1) {
            // Check if this is part of ** (double) — skip it
            bool isDouble = (pos > 0 && result.at(pos - 1) == '*') ||
                           (pos + 1 < result.size() && result.at(pos + 1) == '*');

            if (!isDouble) {
                // This is a single * — check if it has text on both sides
                int start = pos - 1;
                while (start >= 0 && (result.at(start) == ' ' || result.at(start) == '\t')) {
                    start--;
                }
                int end = pos + 1;
                while (end < result.size() && (result.at(end) == ' ' || result.at(end) == '\t')) {
                    end++;
                }

                if (start >= 0 && end < result.size()) {
                    QChar leftChar = result.at(start);
                    QChar rightChar = result.at(end);

                    // Only convert if surrounded by word characters
                    if (leftChar.isLetterOrNumber() && rightChar.isLetterOrNumber()) {
                        // Replace the * with unicode emphasis markers
                        QString replacement = QString(QChar(0x2039)); // ‹
                        result.replace(pos, 1, replacement);
                        pos += replacement.size();
                        continue;
                    }
                }
            }

            pos++;
        }

        // Handle _italic_ (underscore style)
        pos = 0;
        while ((pos = result.indexOf('_', pos)) != -1) {
            // Skip __ (double underscore — already handled by bold)
            if (pos > 0 && result.at(pos - 1) == '_') {
                pos++;
                continue;
            }
            if (pos + 1 < result.size() && result.at(pos + 1) == '_') {
                pos++;
                continue;
            }

            // Single _ — check for closing _
            int endPos = result.indexOf('_', pos + 1);
            if (endPos != -1) {
                // Check it's not part of __
                bool endIsDouble = (endPos > 0 && result.at(endPos - 1) == '_') ||
                                   (endPos + 1 < result.size() && result.at(endPos + 1) == '_');
                if (!endIsDouble) {
                    QString inner = result.mid(pos + 1, endPos - pos - 1);
                    QString emphasized = QString(QChar(0x00AB)) + inner + QString(QChar(0x00BB)); // «text»
                    result.replace(pos, endPos - pos + 1, emphasized);
                    pos += emphasized.size();
                } else {
                    pos++;
                }
            } else {
                break;
            }
        }

        return result;
    }

    /// Convert ~~strikethrough~~ to unicode strikethrough markers.
    static QString convertStrikethrough(QString result) {
        int pos = 0;
        while ((pos = result.indexOf("~~", pos)) != -1) {
            int endPos = result.indexOf("~~", pos + 2);
            if (endPos != -1) {
                QString inner = result.mid(pos + 2, endPos - pos - 2);
                // Replace ~~text~~ with unicode strikethrough markers
                QString emphasized = QString(QChar(0x23CD)) + inner + QString(QChar(0x23CE));
                result.replace(pos, endPos - pos + 2, emphasized);
                pos += emphasized.size();
            } else {
                break;
            }
        }
        return result;
    }

    /// Convert list items (* or - prefix) to unicode bullet points.
    static QString convertListItem(QString line) {
        line.remove(0, 1); // remove the * or -
        while (!line.isEmpty() && (line.at(0) == ' ' || line.at(0) == '\t')) {
            line.remove(0, 1);
        }

        if (line.isEmpty()) {
            return QString();
        }

        return QString(QChar(0x2022)) + " " + line; // • bullet character
    }

    /// Convert numbered list items (1. 2. 3.) to unicode numbered format.
    static QString convertNumberedListItem(QString line) {
        QRegularExpression re("^([0-9]+)\\.\\s+(.*)");
        QRegularExpressionMatch match = re.match(line);
        if (match.hasMatch()) {
            QString num = match.captured(1);
            QString text = match.captured(2);
            // Use unicode subscript numbers for 1-9, regular for 10+
            static const QChar subscriptNums[] = {
                QChar(0x2080), QChar(0x2081), QChar(0x2082), QChar(0x2083),
                QChar(0x2084), QChar(0x2085), QChar(0x2086), QChar(0x2087),
                QChar(0x2088), QChar(0x2089)
            };
            QString numStr;
            for (QChar c : num) {
                if (c.isDigit()) {
                    numStr += subscriptNums[c.digitValue()];
                } else {
                    numStr += c;
                }
            }
            return numStr + QString(QChar(0x2022)) + " " + text; // e.g. ₁• First step
        }
        return line;
    }

    /// Convert blockquotes (> prefix) to unicode-indented text.
    static QString convertBlockquote(QString line) {
        line.remove(0, 1);
        while (!line.isEmpty() && (line.at(0) == ' ' || line.at(0) == '\t')) {
            line.remove(0, 1);
        }

        if (line.isEmpty()) {
            return QString();
        }

        return QString(QChar(0x2502)) + " " + line; // │ prefix
    }

    /// Convert inline code `text` to unicode-marked format.
    static QString convertInlineCode(QString result) {
        int pos = 0;
        while ((pos = result.indexOf('`', pos)) != -1) {
            int endPos = result.indexOf('`', pos + 1);
            if (endPos != -1) {
                QString inner = result.mid(pos + 1, endPos - pos - 1);

                // Skip triple backticks (fence)
                if (endPos + 1 < result.size() && result.at(endPos + 1) == '`') {
                    pos = endPos + 2;
                    continue;
                }

                // Wrap in unicode code font markers
                QString wrapped = QString(QChar(0x200B)) + inner + QString(QChar(0x200B));
                result.replace(pos, endPos - pos + 2, wrapped);
                pos += wrapped.size();
            } else {
                break;
            }
        }
        return result;
    }
};

/// Main application window containing the markdown input and unicode output panes.
class MarkdownViewerWindow : public QMainWindow {
public:
    /// Construct the main window with input/output panes and log panel.
    MarkdownViewerWindow(QWidget *parent = nullptr)
        : QMainWindow(parent) {
        setupUI();
        resize(640, 480);
        setWindowTitle("Markdown → Unicode Converter");
        statusBar()->showMessage("Ready - enter markdown text to convert");
    }

private:
    /// Set up the user interface with splitter panes and log panel.
    void setupUI() {
        // Outer vertical splitter: top = input/output panes, bottom = log panel
        QSplitter *outerSplitter = new QSplitter(Qt::Vertical, this);

        // Inner horizontal splitter for input/output panes
        QSplitter *innerSplitter = new QSplitter(Qt::Horizontal, outerSplitter);

        // Left pane - Markdown input
        inputText = new QTextEdit(innerSplitter);
        inputText->setPlaceholderText("Enter markdown here...\n"
                                      "Supported syntax:\n"
                                      "  # Heading levels\n"
                                      "  **Bold** or __bold__\n"
                                      "  *Italic* or _italic_\n"
                                      "  ~~Strikethrough~~\n"
                                      "  - or * list items\n"
                                      "  > Blockquotes\n"
                                      "  --- Horizontal rule\n"
                                      "  `Inline code`");
        inputText->setFont(QFont("Consolas", 11));
        inputText->setMinimumWidth(300);
        inputText->setStyleSheet(
            "QTextEdit {"
            "  background-color: #ffffff;"
            "  color: #1a1a1a;"
            "  border: 1px solid #cccccc;"
            "  border-radius: 4px;"
            "  padding: 8px;"
            "  selection-background-color: #4a90d9;"
            "}"
        );

        // Right pane - Unicode output display
        outputText = new QTextEdit(innerSplitter);
        outputText->setReadOnly(true);
        outputText->setPlaceholderText("Converted unicode output will appear here...");
        outputText->setFont(QFont("Consolas", 11));
        outputText->setStyleSheet(
            "QTextEdit {"
            "  background-color: #f8f9fa;"
            "  color: #1a1a1a;"
            "  border: 1px solid #cccccc;"
            "  border-radius: 4px;"
            "  padding: 8px;"
            "}"
        );

        // Log panel at bottom of window
        logLabel = new QLabel(outerSplitter);
        logLabel->setMinimumHeight(32);
        logLabel->setStyleSheet(
            "QLabel {"
            "  background-color: #2d2d2d;"
            "  color: #d4d4d4;"
            "  font-size: 11pt;"
            "  font-family: Consolas, monospace;"
            "  padding: 6px 10px;"
            "}"
        );
        logLabel->setText("Ready");

        // Connect input text changed signal to conversion slot
        connect(inputText, &QTextEdit::textChanged, this, &MarkdownViewerWindow::onInputChanged);

        // Set splitter proportions: input 40%, output 60%
        innerSplitter->setStretchFactor(0, 2);
        innerSplitter->setStretchFactor(1, 3);

        // Set splitter proportions: top 85%, log 15%
        outerSplitter->setStretchFactor(0, 17);
        outerSplitter->setStretchFactor(1, 3);

        // Style the splitter handles
        innerSplitter->setStyleSheet(
            "QSplitter::handle {"
            "  background-color: #cccccc;"
            "  border: 1px solid #999999;"
            "}"
            "QSplitter::handle:horizontal {"
            "  width: 4px;"
            "}"
        );

        outerSplitter->setStyleSheet(
            "QSplitter::handle {"
            "  background-color: #cccccc;"
            "  border: 1px solid #999999;"
            "}"
            "QSplitter::handle:vertical {"
            "  height: 4px;"
            "}"
        );

        // Set central widget to the outer splitter
        setCentralWidget(outerSplitter);
    }

    /// Slot: called whenever input text changes, converts and displays output.
    void onInputChanged() {
        QString markdown = inputText->toPlainText();
        bool hasError = false;
        QString errorMsg;

        // Update log immediately
        logMessage("Processing input (" +
                   QString::number(inputText->document()->characterCount()) + " chars)...");

        try {
            // Convert the markdown to unicode
            QString converted = MarkdownToUnicodeConverter::convert(markdown);

            // Display the result
            outputText->setPlainText(converted);

            if (converted.isEmpty() || converted == markdown) {
                logMessage("No conversion changes detected", "info");
            } else {
                logMessage("Conversion complete - " +
                           QString::number(inputText->document()->characterCount()) +
                           " chars → " + QString::number(converted.size()) + " chars",
                           "success");
            }

            statusBar()->showMessage("Converted successfully", 3000);
        } catch (const std::exception &e) {
            hasError = true;
            errorMsg = QString("Conversion exception: %1").arg(e.what());
            logMessage(errorMsg, "error");
            QMessageBox::warning(this, "Conversion Error",
                               QString("An error occurred during markdown conversion:\n%1")
                                   .arg(e.what()));
        } catch (...) {
            hasError = true;
            errorMsg = "Unknown exception during markdown conversion";
            logMessage(errorMsg, "error");
            QMessageBox::critical(this, "Conversion Error",
                               "An unknown error occurred during markdown conversion.");
        }

        // Update status bar
        if (hasError) {
            statusBar()->showMessage("Error: " + errorMsg, 5000);
        }
    }

    /// Append a timestamped message to the log display.
    void logMessage(const QString &message, const QString &type = "info") {
        QString timestamp = QDateTime::currentDateTime().toString("HH:mm:ss");
        QString typeIcon;

        if (type == "success") typeIcon = "✓";
        else if (type == "error") typeIcon = "✗";
        else typeIcon = "•";

        QString formatted = QString("[%1] %2 %3")
                                .arg(timestamp, typeIcon, message);

        logLabel->setText(formatted);
    }

public:
    /// The input text edit widget.
    QTextEdit *inputText;

    /// The output text edit widget (read-only).
    QTextEdit *outputText;

    /// Status label at bottom of main window.
    QLabel *logLabel;
};

/// Application entry point.
int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    app.setOrganizationName("CodingWithGPT");
    app.setApplicationName("MarkdownUnicodeConverter");
    app.setApplicationVersion("1.0.0");

    MarkdownViewerWindow window;
    window.show();

    window.inputText->setFocus();

    return app.exec();
}