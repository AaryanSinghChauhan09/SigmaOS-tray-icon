#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TrayIcon {
    pub id: String,
    pub tooltip: String,
    pub visible: bool,
}

#[derive(Debug, Default)]
pub struct TrayManager {
    icons: Vec<TrayIcon>,
}

impl TrayManager {
    pub fn new() -> Self { Self { icons: Vec::new() } }
    pub fn add_icon(&mut self, id: &str, tooltip: &str) {
        self.icons.push(TrayIcon { id: id.into(), tooltip: tooltip.into(), visible: true });
    }
    pub fn active_count(&self) -> usize {
        self.icons.iter().filter(|i| i.visible).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_tray_manager_aaa() {
        // Arrange
        let mut mgr = TrayManager::new();
        // Act
        mgr.add_icon("music-player", "Playing Track 1");
        // Assert
        assert_eq!(mgr.active_count(), 1);
    }
}
