# Changelog

All notable changes to the Blackmagic HyperDeck Transport Control project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-19

### Added
- **Configuration Management**
  - New `Config` class for centralized constants and settings
  - Configurable polling intervals for connected/disconnected states
  - Centralized deck presets and default values

- **Settings Persistence**
  - New `SettingsManager` class for user preference storage
  - Automatic saving of last selected deck, custom URL, and transport index
  - Settings stored in `~/.hyperdeck_settings.json`
  - Window geometry persistence support (ready for future implementation)

- **Connection Management**
  - New `ConnectionManager` class for connection state tracking
  - Real-time connection status indicator (green/red)
  - Connection health checks with caching to reduce API calls
  - Automatic connection validation with configurable intervals

- **Enhanced API Client**
  - Retry logic with exponential backoff for network requests
  - HTTP session management for better performance
  - LRU caching for transport data to reduce API calls
  - Proper User-Agent and Accept headers
  - Cache invalidation after state-changing operations
  - Comprehensive error handling and logging

- **User Experience Improvements**
  - Keyboard shortcuts: Space (Play), S (Stop), R (Record)
  - Visual connection status indicator in the UI
  - Enhanced status messages with more descriptive feedback
  - Button tooltips showing keyboard shortcuts
  - Improved JSON viewer with better formatting
  - Window title now shows version number

- **Logging System**
  - Comprehensive logging to both file (`hyperdeck.log`) and console
  - Different log levels for different types of messages
  - Detailed error tracking and debugging information
  - Request/response logging for API calls

- **Performance Optimizations**
  - Slower polling when disconnected (5 seconds vs 1 second)
  - Cached connection checks to avoid excessive validation
  - HTTP session reuse for better network performance
  - LRU cache for frequently accessed transport data

### Changed
- **Code Organization**
  - Refactored large GUI class into smaller, focused methods
  - Separated concerns into dedicated manager classes
  - Improved method naming and structure
  - Better separation between UI and business logic

- **Error Handling**
  - More robust network error handling with retry mechanisms
  - Graceful degradation when disconnected
  - Better error messages for users
  - Comprehensive exception handling throughout

- **UI Layout**
  - Added connection status indicator to the connection section
  - Improved button labels with keyboard shortcut hints
  - Better spacing and organization of UI elements
  - Enhanced status bar with more informative messages

- **API Integration**
  - Better handling of different response types
  - Improved parsing of transport state and timecode
  - More reliable active clip detection
  - Enhanced shuttle speed control

### Fixed
- **Network Reliability**
  - Fixed issues with intermittent network failures
  - Improved handling of HTTP errors and timeouts
  - Better recovery from connection losses
  - More stable polling when network is unstable

- **User Experience**
  - Fixed settings not being remembered between sessions
  - Improved feedback when operations fail
  - Better handling of invalid URLs
  - More consistent UI state updates

- **Code Quality**
  - Removed magic numbers and hardcoded values
  - Added comprehensive type hints throughout
  - Improved code documentation and docstrings
  - Better error handling patterns

### Technical Improvements
- **Type Safety**
  - Added comprehensive type hints for all functions and methods
  - Better IDE support and code completion
  - Improved code maintainability

- **Dependencies**
  - Added `certifi` for SSL certificate handling
  - Improved SSL/TLS support for secure connections
  - Better handling of certificate validation

- **Code Structure**
  - Modular design with clear separation of concerns
  - Better testability and maintainability
  - Improved code reusability
  - Cleaner import organization

### Documentation
- **Code Documentation**
  - Added comprehensive docstrings for all public methods
  - Better inline comments and explanations
  - Improved code readability

- **User Documentation**
  - Enhanced README with better setup instructions
  - Added troubleshooting information
  - Better explanation of features and usage

## [1.0.0] - 2024-12-19

### Added
- Initial release of Blackmagic HyperDeck Transport Control
- Basic GUI for controlling HyperDeck devices over network
- Support for multiple deck presets and custom URLs
- Transport controls (play, stop, record, shuttle)
- Real-time status polling and display
- JSON viewer for debugging API responses
- Support for multiple transport indices (0-7)

### Features
- Connect to HyperDeck units via IP over local network
- Remote control playback, stop, record, and shuttle functions
- Live status updates from HyperDeck REST API
- Lightweight GUI built with Tkinter
- Support for HyperDeck Studio 4K models
- Custom URL support for non-preset devices

---

## Migration Guide

### From v1.0.0 to v2.0.0

1. **Settings Migration**: v2.0.0 will automatically create a new settings file. Your previous custom URLs and preferences will need to be re-entered.

2. **New Features**: 
   - Keyboard shortcuts are now available (Space, S, R)
   - Connection status indicator shows real-time connection state
   - Settings are automatically saved and restored

3. **Performance**: The new version is more efficient and reliable, with better error handling and network resilience.

4. **Logging**: Check `hyperdeck.log` for detailed operation logs and debugging information.

### Breaking Changes
- None - the v2.0.0 API is backward compatible with v1.0.0
- Settings format has changed, but old settings will be ignored gracefully

---

## Future Roadmap

### Planned Features
- [ ] Multi-deck support (control multiple devices simultaneously)
- [ ] Clip browser and selection
- [ ] Timeline scrubber for seeking
- [ ] Configuration file support (YAML/JSON)
- [ ] Plugin system for custom controls
- [ ] Web interface option
- [ ] Mobile app companion
- [ ] Advanced logging and analytics
- [ ] Automated testing suite
- [ ] Docker containerization

### Known Issues
- None currently identified

---

## Contributing

Please see the main README.md for contribution guidelines and development setup instructions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
