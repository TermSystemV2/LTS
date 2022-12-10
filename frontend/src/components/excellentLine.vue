<template>
    <div ref="excellentLineRef" class="chart">

    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentLineData } from '../api/index';

const excellentLineRef = ref<HTMLDivElement>()
onMounted(() => {
    fetchExcellentLineData().then(res => {
        console.log(res.data);
        let data = res.data.data;
        let year = [];
        let series = []
        for (var key in data) {
            let year_name = key.slice(2) + '级'
            year.push(year_name)
            var dict = {
                name: year_name,
                type: 'line',
                tooltip: {
                    valueFormatter: function (value: string) {
                        return value + ' %';
                    }
                },
                data: [] as any
            };
            let d = data[key]
            let arr = new Array(3).fill(0);
            for(var k in d){
                if(k == 'grade1'){
                    arr[0]=d[k].excellentRate
                }
                else if(k == 'grade2'){
                    arr[1]=d[k].excellentRate
                }
                else if(k == 'grade3'){
                    arr[2]=d[k].excellentRate
                }
            }
            dict.data = arr;
            series.push(dict)
        }
        // 基于准备好的dom，初始化echarts实例
        var myChart = echarts.init(excellentLineRef.value as HTMLDivElement, 'macarons');
        var option = {
            title: {
                text: ''
            },
            tooltip: {
                trigger: 'axis'
            },
            legend: {
                data: year
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            toolbox: {
                feature: {
                    dataView: { show: true, readOnly: false },
                    magicType: { show: true, type: ['line', 'bar'] },
                    restore: { show: true },
                    saveAsImage: { show: true }
                }
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: ['大一', '大二', '大三']
            },
            yAxis: {
                type: 'value',
                min: 0,
                max: 100,
                interval: 10,
                axisLabel: {
                    formatter: '{value} %'
                }
            },
            series: series
            // series: [
            //     {
            //         name: '16级',
            //         type: 'line',
            //         tooltip: {
            //             valueFormatter: function (value: string) {
            //                 return value + ' %';
            //             }
            //         },
            //         data: [20, 32, 10]
            //     },
            //     {
            //         name: '17级',
            //         type: 'line',
            //         tooltip: {
            //             valueFormatter: function (value: string) {
            //                 return value + ' %';
            //             }
            //         },
            //         data: [20, 82, 91]
            //     },
            //     {
            //         name: '18级',
            //         type: 'line',
            //         tooltip: {
            //             valueFormatter: function (value: string) {
            //                 return value + ' %';
            //             }
            //         },
            //         data: [50, 32, 20]
            //     },
            //     {
            //         name: '19级',
            //         type: 'line',
            //         tooltip: {
            //             valueFormatter: function (value: string) {
            //                 return value + ' %';
            //             }
            //         },
            //         data: [20, 32, 30]
            //     },
            //     {
            //         name: '20级',
            //         type: 'line',
            //         tooltip: {
            //             valueFormatter: function (value: string) {
            //                 return value + ' %';
            //             }
            //         },
            //         data: [82, 93, 90]
            //     }
            // ]
        };
        // 绘制图表
        myChart.setOption(option);
        window.addEventListener('resize', () => {
            myChart.resize()
        })
    })
})
</script>
<style scoped>
.chart {
    width: 90%;
    height: 80%;
}
</style>