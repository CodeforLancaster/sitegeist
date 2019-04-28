import React, { Component } from 'react'
import './App.css'
import Header from './components/Header/Header'
import MapContainer from './components/MapContainer/MapContainer'
import ChartContainer from './components/charts/ChartContainer/ChartContainer'
import Info from './components/Info/Info'

class App extends Component {
  render() {
    return (
      <div className="App">
        <Header/>
        <MapContainer/>
        <ChartContainer/>
        <Info/>
      </div>
    )
  }
}

export default App
