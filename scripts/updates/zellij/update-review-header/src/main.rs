use std::collections::BTreeMap;
use std::io::Write;
use zellij_tile::prelude::*;

#[derive(Default)]
struct UpdateReviewHeader {
    detach_allowed: bool,
    last_columns: usize,
}

register_plugin!(UpdateReviewHeader);

// Mouse coordinates belong to the dedicated header pane (title + divider).
// Never detach for clicks in the divider or the update transcript.
fn close_hit(line: isize, col: usize, columns: usize) -> bool {
    line == 0 && columns >= 18 && col >= columns.saturating_sub(5) && col < columns
}

// Terminal panes use cells, not pixel units. Half-cell box-drawing caps
// bring the cyan rule closer to the window sides without touching either wall.
fn divider_line(columns: usize) -> String {
    match columns {
        0 => String::new(),
        1 => "╶".to_string(),
        _ => format!("╶{}╴", "─".repeat(columns - 2)),
    }
}

impl ZellijPlugin for UpdateReviewHeader {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        subscribe(&[EventType::Mouse, EventType::PermissionRequestResult]);
        request_permission(&[PermissionType::ChangeApplicationState]);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                self.detach_allowed = true;
                true
            }
            Event::PermissionRequestResult(PermissionStatus::Denied) => {
                self.detach_allowed = false;
                true
            }
            Event::Mouse(Mouse::LeftClick(line, column)) => {
                if self.detach_allowed && close_hit(line, column, self.last_columns) {
                    // Detach, NEVER close pane, quit_zellij or kill the
                    // process. Detached installations remain in Zellij.
                    detach();
                }
                false
            }
            _ => false,
        }
    }

    fn render(&mut self, rows: usize, columns: usize) {
        self.last_columns = columns;
        if rows == 0 || columns == 0 {
            return;
        }
        let title = " POST-APOLLO // UPDATE REVIEW";
        let x = "[ \u{00d7} ]";
        let title_chars = title.chars().count();
        let x_chars = x.chars().count();
        let printable = if columns >= title_chars + x_chars {
            format!("{}{}{}", title, " ".repeat(columns - title_chars - x_chars), x)
        } else if columns >= x_chars {
            format!("{}{}", " ".repeat(columns - x_chars), x)
        } else {
            " ".repeat(columns)
        };
        // The header is magenta; the interactive X is red only after the
        // operator granted the minimal ChangeApplicationState permission.
        // This plugin never reads update contents or invokes the updater.
        let prefix_len = printable.len().saturating_sub(x.len());
        let (prefix, close) = printable.split_at(prefix_len);
        let x_color = if self.detach_allowed {
            "\x1b[38;2;209;96;65m"
        } else {
            "\x1b[38;2;110;110;110m"
        };
        print!("\x1b[48;2;27;6;35m\x1b[38;2;199;78;199m{}{}{}\x1b[0m",
               prefix, x_color, close);
        if rows >= 2 {
            // Absolute cursor placement avoids an accidental extra wrap after
            // the full-width first row. This second row is never clickable.
            print!("\x1b[2;1H\x1b[48;2;27;6;35m\x1b[38;2;85;207;202m{}\x1b[0m",
                   divider_line(columns));
        }
        let _ = std::io::stdout().flush();
    }
}

#[cfg(test)]
mod tests {
    use super::{close_hit, divider_line};

    #[test]
    fn x_only_in_right_edge_of_title_row() {
        assert!(close_hit(0, 76, 80));
        assert!(close_hit(0, 79, 80));
        assert!(!close_hit(0, 74, 80));
        assert!(!close_hit(1, 79, 80)); // Divider row cannot detach
        assert!(!close_hit(-1, 79, 80));
        assert!(!close_hit(0, 80, 80));
        assert!(!close_hit(0, 5, 10));
    }

    #[test]
    fn cyan_divider_inset_from_both_edges() {
        let row = divider_line(80);
        assert_eq!(row.chars().count(), 80);
        // Half-cell caps leave air on both sides, unlike full-width lines.
        assert!(row.starts_with("╶─"));
        assert!(row.ends_with("─╴"));
        assert_eq!(row.chars().filter(|&ch| ch == '─').count(), 78);
        assert_eq!(divider_line(0), "");
        assert_eq!(divider_line(1), "╶");
        assert_eq!(divider_line(2), "╶╴");
        assert_eq!(divider_line(3), "╶─╴");
    }
}
