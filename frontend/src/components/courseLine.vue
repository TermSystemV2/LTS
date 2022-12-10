<template>
    <div ref="courseLineRef" class="chart">
        <!-- <p>{{ fatherDataName }}</p> -->
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, defineProps } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentBarData } from '../api/index';

const props = defineProps({
    chartData: Object,
});
const courseLineRef = ref<HTMLDivElement>()
onMounted(() => {
    let data = props.chartData;
    let courseName = data?.courseName;
    let gradeDistribute = data?.gradeDistribute;
    let grade = []
    let series = []
    for (var key in gradeDistribute) {
        let grade_name = '20'+key + '年'
        grade.push(grade_name)
        let scoreDistribute = gradeDistribute[key]
        let count = []
        for(var score in scoreDistribute){
            count.push(scoreDistribute[score])
        }
        var dict = {
            name: grade_name,
            type: 'line',
            tooltip: {
                valueFormatter: function (value: string) {
                    return value + ' 个';
                }
            },
            data: count
        };
        series.push(dict)
    }
    // 基于准备好的dom，初始化echarts实例
    var myChart = echarts.init(courseLineRef.value as HTMLDivElement, 'macarons');
        var option = {
            title: {
                text: ''
            },
            tooltip: {
                trigger: 'axis'
            },
            legend: {
                data: grade
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
                data: ['0-59分', '60-69分', '70-79分', '80-89分', '90-100分']
            },
            yAxis: {
                type: 'value',
                min: 0,
                max: 100,
                interval: 10,
                axisLabel: {
                    formatter: '{value} 个'
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
</script>
<style scoped>
.chart {
    width: 700px;
    height: 500px;
}
</style>