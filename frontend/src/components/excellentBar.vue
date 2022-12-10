<template>
    <div ref="excellentBarRef" class="chart">

    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentBarData } from '../api/index';

const excellentBarRef = ref<HTMLDivElement>()
onMounted(() => {
    fetchExcellentBarData().then(res => {
        let data = res.data.data;
        let year = []
        let excellentNum = []
        let excellentRate = []
        for (var key in data) {
            year.push(key+'年')
            excellentNum.push(data[key].excellentStudyClassNum)
            excellentRate.push(data[key].excellentRate)
        }
        // 基于准备好的dom，初始化echarts实例
        var myChart = echarts.init(excellentBarRef.value as HTMLDivElement, 'macarons');
        var option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross',
                    crossStyle: {
                        color: '#999'
                    }
                }
            },
            toolbox: {
                feature: {
                    dataView: { show: true, readOnly: false },
                    magicType: { show: true, type: ['line', 'bar'] },
                    restore: { show: true },
                    saveAsImage: { show: true }
                }
            },
            legend: {
                data: ['个数', '比例']
            },
            xAxis: [
                {
                    type: 'category',
                    data: year,
                    axisPointer: {
                        type: 'shadow'
                    }
                }
            ],
            yAxis: [
                {
                    type: 'value',
                    name: '个数',
                    min: 0,
                    max: 35,
                    interval: 5,
                    axisLabel: {
                        formatter: '{value} 个'
                    }
                },
                {
                    type: 'value',
                    name: '比例',
                    min: 0,
                    max: 100,
                    interval: 10,
                    axisLabel: {
                        formatter: '{value} %'
                    }
                }
            ],
            series: [
                {
                    name: '个数',
                    type: 'bar',
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' 个';
                        }
                    },
                    data: excellentNum
                },
                {
                    name: '比例',
                    type: 'line',
                    yAxisIndex: 1,
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' %';
                        }
                    },
                    data: excellentRate
                }
            ]
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