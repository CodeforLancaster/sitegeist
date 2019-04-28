import { ResponsiveBar } from '@nivo/bar'
import React, { Component } from 'react'
import './BarChart.css'

// make sure parent container have a defined height when using
// responsive component, otherwise height will be 0 and
// no chart will be rendered.
// website examples showcase many properties,
// you'll often use just a few of them.
export const ResponsiveBarStyled = ({ name, data /* see data tab */ }) => (
    <div className="chart">
        <h2>{name}</h2>
        <ResponsiveBar
            data={data}
            keys={[
                "sentiment",
            ]}
            indexBy="topic"
            margin={{
                "top": 0,
                "right": 16,
                "bottom": 0,
                "left": 16
            }}
            padding={0.3}
            layout="horizontal"
            colors={{
                "scheme": "category10"
            }}
            defs={[
                {
                    "id": "dots",
                    "type": "patternDots",
                    "background": "inherit",
                    "color": "#38bcb2",
                    "size": 4,
                    "padding": 1,
                    "stagger": true
                },
                {
                    "id": "lines",
                    "type": "patternLines",
                    "background": "inherit",
                    "color": "#eed312",
                    "rotation": -45,
                    "lineWidth": 6,
                    "spacing": 10
                }
            ]}
            fill={[
                {
                    "match": {
                        "id": "fries"
                    },
                    "id": "dots"
                },
                {
                    "match": {
                        "id": "sandwich"
                    },
                    "id": "lines"
                }
            ]}
            borderColor={{
                "from": "color",
                "modifiers": [
                    [
                        "darker",
                        1.6
                    ]
                ]
            }}
            axisTop={null}
            axisRight={null}
            axisBottom={null}
            axisLeft={null}
            label={d => `${d.indexValue}`}
            labelSkipWidth={12}
            labelSkipHeight={12}
            labelTextColor="#ffffff"
            tooltip={d => {
                return (
                    <div>
                        <p><b>{d.indexValue}</b></p>
                        <p>Sentiment: {d.value}</p>
                        <p>Tweets: {d.data.tweets}</p>
                    </div>
                )
            }}
            legends={[]}
            animate={true}
            motionStiffness={90}
            motionDamping={15}
        />
    </div>
)