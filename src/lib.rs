// SPDX-License-Identifier: Apache-2.0
//! SigmaOS-tray-icon — SigmaOS tray-icon component inspired by Linux Mint / Omarchy / Arch Linux.
//!
//! Theme/asset registry: name -> resource path with uniqueness and non-empty validation.
//! Principles: single responsibility, fail-fast, defensive programming,
//! component isolation, stable API, deterministic tests.

#![forbid(unsafe_code)]

use std::fmt;
use std::collections::BTreeMap;

/// Errors for `AssetError` operations. Fail-fast: invalid input is rejected.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AssetError {
    /// Asset name must not be empty
    EmptyName,
    /// Asset path must not be empty
    EmptyPath(String),
    /// Asset name already registered
    Duplicate(String),
    /// Asset not registered
    NotFound(String),
}

impl fmt::Display for AssetError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyName => write!(f, "asset name must not be empty"),
            Self::EmptyPath(x) => write!(f, "asset path must not be empty: {x}"),
            Self::Duplicate(x) => write!(f, "asset name already registered: {x}"),
            Self::NotFound(x) => write!(f, "asset not registered: {x}"),
        }
    }
}

impl std::error::Error for AssetError {}

/// Registry mapping asset names to resource paths.
#[derive(Debug, Default)]
pub struct AssetRegistry {
    assets: BTreeMap<String, String>,
}

impl AssetRegistry {
    /// Empty registry.
    pub fn new() -> Self { Self::default() }

    /// Register an asset; fails on empty name/path or duplicate name.
    pub fn register(&mut self, name: impl Into<String>, path: impl Into<String>) -> Result<(), AssetError> {
        let name = name.into();
        let path = path.into();
        if name.trim().is_empty() { return Err(AssetError::EmptyName); }
        if path.trim().is_empty() { return Err(AssetError::EmptyPath(name)); }
        if self.assets.contains_key(&name) { return Err(AssetError::Duplicate(name)); }
        self.assets.insert(name, path);
        Ok(())
    }

    /// Resolve an asset name to its path.
    pub fn resolve(&self, name: &str) -> Result<&str, AssetError> {
        self.assets.get(name).map(String::as_str)
            .ok_or_else(|| AssetError::NotFound(name.to_string()))
    }

    /// Number of assets.
    pub fn len(&self) -> usize { self.assets.len() }

    /// Whether empty.
    pub fn is_empty(&self) -> bool { self.assets.is_empty() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn register_and_resolve() {
        let mut r = AssetRegistry::new();
        r.register("wallpaper", "/usr/share/wall.png").unwrap();
        assert_eq!(r.resolve("wallpaper").unwrap(), "/usr/share/wall.png");
    }

    #[test]
    fn duplicate_fails() {
        let mut r = AssetRegistry::new();
        r.register("a", "/p").unwrap();
        assert!(matches!(r.register("a", "/q"), Err(AssetError::Duplicate(_))));
    }

    #[test]
    fn empty_path_fails() {
        let mut r = AssetRegistry::new();
        assert!(matches!(r.register("a", " "), Err(AssetError::EmptyPath(_))));
    }

    #[test]
    fn resolve_missing_fails() {
        assert!(matches!(AssetRegistry::new().resolve("x"), Err(AssetError::NotFound(_))));
    }

}

/// Backwards-compatible component handle (kept for existing callers/tests).
#[derive(Debug, Default)]
pub struct Component {
    name: &'static str,
}

impl Component {
    /// Create the component handle.
    pub fn new() -> Self {
        Self { name: "SigmaOS Component" }
    }
}
